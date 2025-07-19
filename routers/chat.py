from fastapi import APIRouter, Depends, HTTPException, status
from fastapi.responses import StreamingResponse
from sqlalchemy.orm import Session
from typing import List
import json
import asyncio
import httpx
from database import SessionLocal
from schemas.chat import ChatMessage, ChatHistory, ChatResponse
from crud.user import get_user_by_userId
from crud.etf import get_user_settings
from crud.chat import save_message, get_chat_history_asc, get_message_count
from utils.auth import get_current_user

router = APIRouter()

def get_db():
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()

@router.get("/chat/history", response_model=ChatHistory)
def get_user_chat_history(
    limit: int = 50,
    db: Session = Depends(get_db),
    current_user: str = Depends(get_current_user)
):
    """사용자의 대화 히스토리 조회"""
    user = get_user_by_userId(db, current_user)
    if not user:
        raise HTTPException(status_code=404, detail="사용자를 찾을 수 없습니다.")
    
    messages = get_chat_history_asc(db, int(user.id), limit)
    total_count = get_message_count(db, int(user.id))
    
    return ChatHistory(messages=messages, total_count=total_count)

@router.post("/chat/stream")
async def send_message_stream(
    message: ChatResponse,
    current_user: str = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    """챗봇에 메시지 전송 (스트리밍 응답)"""
    user = get_user_by_userId(db, current_user)
    if not user:
        raise HTTPException(status_code=404, detail="사용자를 찾을 수 없습니다.")
    
    # 1. 사용자 메시지를 DB에 저장
    save_message(db, int(user.id), "user", message.content)
    
    # 2. 사용자의 전체 대화 히스토리 조회 (시간순)
    chat_history = get_chat_history_asc(db, int(user.id))
    
    # 3. AI 서버용 메시지 형식으로 변환
    messages = [
        {"role": msg.role, "content": msg.content} 
        for msg in chat_history
    ]
    
    # 4. 사용자 설정 가져오기
    settings = get_user_settings(db, int(user.id))
    if not settings:
        raise HTTPException(status_code=404, detail="설정을 찾을 수 없습니다.")
    api_key = settings.api_key
    model_type = settings.model_type
    
    async def generate_stream():
        try:
            # 5. AI 서버에 전체 대화 히스토리 전송
            async with httpx.AsyncClient() as client:
                response = await client.post(
                    "http://localhost:8001/chat/stream",
                    json={
                        "messages": messages,  # 전체 대화 히스토리
                        "api_key": api_key,
                        "model_type": model_type
                    },
                    timeout=60.0
                )
                response.raise_for_status()
                
                full_response = ""
                async for line in response.aiter_lines():
                    if line.startswith('data: '):
                        data = line[6:]  # 'data: ' 제거
                        if data == '[DONE]':
                            break
                        try:
                            parsed = json.loads(data)
                            if 'content' in parsed:
                                full_response += parsed['content']
                                yield f"data: {json.dumps({'content': parsed['content']})}\n\n"
                        except json.JSONDecodeError:
                            yield f"data: {json.dumps({'content': data})}\n\n"
                
                # 6. AI 응답을 DB에 저장
                save_message(db, int(user.id), "assistant", full_response)
                
                yield "data: [DONE]\n\n"
                            
        except Exception as e:
            error_message = f"AI 서비스 오류: {str(e)}"
            yield f"data: {json.dumps({'content': error_message})}\n\n"
            yield "data: [DONE]\n\n"
    
    return StreamingResponse(
        generate_stream(),
        media_type="text/plain",
        headers={
            "Cache-Control": "no-cache",
            "Connection": "keep-alive",
            "Content-Type": "text/event-stream"
        }
    ) 