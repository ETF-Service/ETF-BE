from fastapi import APIRouter, Depends, HTTPException
from fastapi.responses import StreamingResponse
from sqlalchemy.orm import Session
from typing import List
import json
import asyncio
from database import SessionLocal
from schemas.chat import ChatMessage, ChatResponse
from crud.user import get_user_by_username
from crud.etf import get_user_portfolios, get_user_settings
from utils.auth import get_current_user
from services.ai_service import AIService

router = APIRouter()

def get_db():
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()

@router.post("/chat", response_model=ChatResponse)
async def send_message(
    message: ChatMessage,
    current_user: str = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    """챗봇에 메시지 전송 (일반 응답)"""
    user = get_user_by_username(db, current_user)
    if not user:
        raise HTTPException(status_code=404, detail="사용자를 찾을 수 없습니다.")
    
    # 사용자 포트폴리오 및 설정 가져오기
    portfolios = get_user_portfolios(db, user.id)
    settings = get_user_settings(db, user.id)
    
    # AI 서비스 호출
    ai_service = AIService()
    try:
        response = await ai_service.get_response(
            message=message.content,
            user_name=user.name,
            portfolios=portfolios,
            settings=settings
        )
        return ChatResponse(content=response)
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"AI 서비스 오류: {str(e)}")

@router.post("/chat/stream")
async def send_message_stream(
    message: ChatMessage,
    current_user: str = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    """챗봇에 메시지 전송 (스트리밍 응답)"""
    user = get_user_by_username(db, current_user)
    if not user:
        raise HTTPException(status_code=404, detail="사용자를 찾을 수 없습니다.")
    
    # 사용자 포트폴리오 및 설정 가져오기
    portfolios = get_user_portfolios(db, user.id)
    settings = get_user_settings(db, user.id)
    
    async def generate_stream():
        ai_service = AIService()
        try:
            async for chunk in ai_service.get_response_stream(
                message=message.content,
                user_name=user.name,
                portfolios=portfolios,
                settings=settings
            ):
                yield f"data: {json.dumps({'content': chunk})}\n\n"
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