from fastapi import APIRouter, Depends, HTTPException, status
from fastapi.responses import StreamingResponse
from sqlalchemy.orm import Session
from typing import List
import json
import asyncio
import requests
from database import SessionLocal
from schemas.chat import ChatMessage, ChatResponse
from crud.user import get_user_by_userId
from crud.etf import get_user_portfolios, get_user_settings
from utils.auth import get_current_user
from models import chat as chat_model

router = APIRouter()

def get_db():
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()

@router.post("/chats", response_model=ChatResponse)
def chat_with_ai(
    message: ChatMessage,
    db: Session = Depends(get_db),
    current_user: str = Depends(get_current_user)
):
    """
    사용자의 질문을 받아 AI 서버에 전달하고, 답변을 받아 DB에 저장 후 반환
    """
    # 1. 사용자 정보 및 설정 가져오기
    user = get_user_by_userId(db, current_user)
    if not user:
        raise HTTPException(status_code=404, detail="사용자를 찾을 수 없습니다.")
    
    settings = get_user_settings(db, user_id=user.id)
    api_key = settings.api_key if settings else "default-api-key"
    model_type = settings.model_type if settings else "gpt-3.5-turbo"
    
    # 2. AI 서버에 직접 요청 (스트리밍으로 받아서 전체 답변 수집)
    
    payload = {
        "question": message.content,
        "api_key": api_key,
        "model_type": model_type
    }
    
    try:
        response = requests.post(
            "http://localhost:8001/chat/stream",
            json=payload,
            stream=True,
            timeout=60
        )
        response.raise_for_status()
        
        ai_answer = ""
        for line in response.iter_lines():
            if line:
                line_str = line.decode('utf-8')
                if line_str.startswith('data: '):
                    data = line_str[6:]  # 'data: ' 제거
                    if data == '[DONE]':
                        break
                    try:
                        parsed = json.loads(data)
                        if 'content' in parsed:
                            ai_answer += parsed['content']
                    except json.JSONDecodeError:
                        # JSON이 아닌 경우 그대로 추가
                        ai_answer += data
                        
    except Exception as e:
        ai_answer = f"AI 서비스 오류: {str(e)}"

    # 3. DB에 질문/답변 저장
    chat_history = chat_model.ChatHistory(
        user_id=user.id,  # 실제 데이터베이스 ID (정수)
        question=message.content,
        answer=ai_answer
    )
    db.add(chat_history)
    db.commit()
    db.refresh(chat_history)

    # 4. 답변 반환
    return ChatResponse(answer=ai_answer)

@router.post("/chats/stream")
async def send_message_stream(
    message: ChatMessage,
    current_user: str = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    """챗봇에 메시지 전송 (스트리밍 응답)"""
    user = get_user_by_userId(db, current_user)
    if not user:
        raise HTTPException(status_code=404, detail="사용자를 찾을 수 없습니다.")
    
    # 사용자 설정 가져오기
    settings = get_user_settings(db, user.id)
    if not settings:
        raise HTTPException(status_code=404, detail="설정을 찾을 수 없습니다.")
    api_key = settings.api_key
    model_type = settings.model_type
    
    async def generate_stream():
        try:
            # AI 서버의 스트리밍 엔드포인트에 직접 요청
            import requests
            
            payload = {
                "question": message.content,
                "api_key": api_key,
                "model_type": model_type
            }
            
            response = requests.post(
                "http://localhost:8001/chat/stream",
                json=payload,
                stream=True,
                timeout=60
            )
            response.raise_for_status()
            
            # AI 서버에서 오는 스트리밍 데이터를 그대로 전달
            for line in response.iter_lines():
                if line:
                    line_str = line.decode('utf-8')
                    if line_str.startswith('data: '):
                        data = line_str[6:]  # 'data: ' 제거
                        if data == '[DONE]':
                            break
                        try:
                            parsed = json.loads(data)
                            if 'content' in parsed:
                                yield f"data: {json.dumps({'content': parsed['content']})}\n\n"
                        except json.JSONDecodeError:
                            # JSON이 아닌 경우 그대로 yield
                            yield f"data: {json.dumps({'content': data})}\n\n"
                            
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