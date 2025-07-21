from fastapi import APIRouter, Depends, HTTPException, status
from fastapi.responses import StreamingResponse
from sqlalchemy.orm import Session
import json
import httpx
from database import SessionLocal, get_db
from schemas.chat import ChatHistory, ChatResponse
from crud.user import get_user_by_userId
from crud.etf import get_user_settings
from crud.chat import save_message, get_chat_history_asc, get_message_count
from utils.auth import get_current_user

router = APIRouter()

# 대화 히스토리 조회
@router.get("/chat/history", response_model=ChatHistory)
def get_user_chat_history(
    limit: int = 50,
    db: Session = Depends(get_db),
    current_user: str = Depends(get_current_user)
):
    user = get_user_by_userId(db, current_user)
    if not user:
        raise HTTPException(status_code=404, detail="사용자를 찾을 수 없습니다.")
    user_id = getattr(user, 'id')
    messages = get_chat_history_asc(db, user_id, limit)
    total_count = len(messages)
    
    return ChatHistory(messages=messages, total_count=total_count)

# 대화 스트리밍 전송
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
    user_id = getattr(user, 'id')
    save_message(db, user_id, "user", message.content)

    # 2. 페르소나 설정
    setting = get_user_settings(db, user_id)
    if not setting:
        raise HTTPException(status_code=404, detail="설정을 찾을 수 없습니다.")
    persona = setting.persona
    
    messages = []
    messages.append({"role": "developer", "content": persona})
    
    # 3. 사용자의 전체 대화 히스토리 조회 (시간순)
    chat_history = get_chat_history_asc(db, user_id)
    
    # 4. AI 서버용 메시지 형식으로 변환
    for msg in chat_history:
        messages.append({"role": msg.role, "content": msg.content})
    
    # 5. 사용자 설정 가져오기
    api_key = setting.api_key
    model_type = setting.model_type
    
    async def generate_stream():
        try:
            # 6. AI 서버에 전체 대화 히스토리 전송
            async with httpx.AsyncClient() as client:
                async with client.stream(
					"POST",
                    "http://localhost:8001/chat/stream",
                    json={
                        "messages": messages,  # 전체 대화 히스토리
                        "api_key": api_key,
                        "model_type": model_type
                    },
                    timeout=60.0
                ) as response:
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
                    
                    # 7. AI 응답을 DB에 저장
                    save_message(db, user_id, "assistant", full_response)
                    
                    yield "data: [DONE]\n\n"
                            
        except Exception as e:
            error_message = f"AI 서비스 오류: {str(e)}"
            yield f"data: {json.dumps({'content': error_message})}\n\n"
            yield "data: [DONE]\n\n"
    
    return StreamingResponse(
        generate_stream(),
        media_type="text/event-stream",
        headers={
            "Cache-Control": "no-cache",
            "Connection": "keep-alive",
        }
    ) 