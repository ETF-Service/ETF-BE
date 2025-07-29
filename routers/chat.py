from fastapi import APIRouter, Depends, HTTPException, status
from fastapi.responses import StreamingResponse
from sqlalchemy.orm import Session
import json
import httpx
import logging
import os
from database import get_db
from schemas.chat import ChatHistory, ChatResponse
from crud.user import get_user_by_userId
from crud.etf import get_investment_settings_by_user_id
from crud.chat import save_message, get_chat_history_asc, get_message_count
from utils.auth import get_current_user

# 로거 설정
logger = logging.getLogger(__name__)

# AI 서비스 URL 환경변수에서 가져오기 (기본값: localhost:8001)
AI_SERVICE_URL = os.getenv("ETF_AI_SERVICE_URL", "http://localhost:8001")

router = APIRouter()

# 대화 히스토리 조회
@router.get("/chat/history", response_model=ChatHistory)
def get_user_chat_history(
    limit: int = 50,
    db: Session = Depends(get_db),
    current_user: str = Depends(get_current_user)
):
    """사용자의 대화 히스토리 조회"""
    try:
        user = get_user_by_userId(db, current_user)
        if not user:
            raise HTTPException(status_code=404, detail="사용자를 찾을 수 없습니다.")
        
        user_id = getattr(user, 'id')
        messages = get_chat_history_asc(db, user_id, limit)
        total_count = get_message_count(db, user_id)
        
        return ChatHistory(messages=messages, total_count=total_count)
        
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"대화 히스토리 조회 실패: {str(e)}")
        raise HTTPException(status_code=500, detail="대화 히스토리 조회 중 오류가 발생했습니다.")

# 대화 스트리밍 전송
@router.post("/chat/stream")
async def send_message_stream(
    message: ChatResponse,
    current_user: str = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    """챗봇에 메시지 전송 (스트리밍 응답)"""
    try:
        # 1. 사용자 검증
        user = get_user_by_userId(db, current_user)
        if not user:
            raise HTTPException(status_code=404, detail="사용자를 찾을 수 없습니다.")
        
        user_id = getattr(user, 'id')
        
        # 2. 사용자 메시지를 DB에 저장
        save_message(db, user_id, "user", message.content)
        
        # 3. 사용자 설정 조회
        setting = get_investment_settings_by_user_id(db, user_id)
        if not setting:
            raise HTTPException(status_code=404, detail="투자 설정을 찾을 수 없습니다.")
        
        persona = setting.persona
        api_key = setting.api_key
        model_type = setting.model_type
        
        # 4. 최근 대화 히스토리 조회 (메모리 효율성을 위해 최근 20개만)
        recent_messages = get_chat_history_asc(db, user_id, limit=20)
        
        # 5. AI 서버용 메시지 형식으로 변환
        messages = [{"role": "developer", "content": persona}]
        for msg in recent_messages:
            messages.append({"role": msg.role, "content": msg.content})
        
        # 6. 현재 메시지 추가
        messages.append({"role": "user", "content": message.content})
        
        async def generate_stream():
            try:
                # 7. AI 서버에 요청 전송
                async with httpx.AsyncClient() as client:
                    async with client.stream(
                        "POST",
                        f"{AI_SERVICE_URL}/chat/stream",
                        json={
                            "messages": messages,
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
                        
                        # 8. AI 응답을 DB에 저장
                        if full_response.strip():  # 빈 응답이 아닌 경우만 저장
                            save_message(db, user_id, "assistant", full_response)
                        
                        yield "data: [DONE]\n\n"
                                
            except httpx.TimeoutException:
                error_message = "AI 서비스 응답 시간이 초과되었습니다. 잠시 후 다시 시도해주세요."
                logger.warning(f"AI 서비스 타임아웃 - 사용자: {current_user}")
                yield f"data: {json.dumps({'content': error_message})}\n\n"
                yield "data: [DONE]\n\n"
                
            except httpx.HTTPStatusError as e:
                error_message = f"AI 서비스 오류 (HTTP {e.response.status_code})"
                logger.error(f"AI 서비스 HTTP 오류 - 사용자: {current_user}, 상태: {e.response.status_code}")
                yield f"data: {json.dumps({'content': error_message})}\n\n"
                yield "data: [DONE]\n\n"
                
            except Exception as e:
                error_message = "AI 서비스와의 통신 중 오류가 발생했습니다."
                logger.error(f"AI 서비스 통신 오류 - 사용자: {current_user}, 오류: {str(e)}")
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
        
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"채팅 스트림 처리 실패 - 사용자: {current_user}, 오류: {str(e)}")
        raise HTTPException(status_code=500, detail="채팅 처리 중 오류가 발생했습니다.") 