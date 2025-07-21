from sqlalchemy.orm import Session
from models.chat import ChatMessage
from typing import List

def save_message(db: Session, user_id: int, role: str, content: str) -> ChatMessage:
    """대화 메시지를 데이터베이스에 저장"""
    db_message = ChatMessage(
        user_id=user_id,
        role=role,
        content=content
    )
    db.add(db_message)
    db.commit()
    db.refresh(db_message)
    return db_message

def get_chat_history(db: Session, user_id: int, limit: int = 50) -> List[ChatMessage]:
    """사용자의 대화 히스토리를 조회 (최신순)"""
    return db.query(ChatMessage)\
        .filter(ChatMessage.user_id == user_id)\
        .order_by(ChatMessage.created_at.desc())\
        .limit(limit)\
        .all()

def get_chat_history_asc(db: Session, user_id: int, limit: int = 50) -> List[ChatMessage]:
    """사용자의 대화 히스토리를 조회 (시간순) - AI 서버용"""
    return db.query(ChatMessage)\
        .filter(ChatMessage.user_id == user_id)\
        .order_by(ChatMessage.created_at.asc())\
        .limit(limit)\
        .all()

def delete_chat_history(db: Session, user_id: int) -> bool:
    """사용자의 모든 대화 히스토리 삭제"""
    deleted_count = db.query(ChatMessage)\
        .filter(ChatMessage.user_id == user_id)\
        .delete()
    db.commit()
    return deleted_count > 0

def get_message_count(db: Session, user_id: int) -> int:
    """사용자의 대화 메시지 개수 조회"""
    return db.query(ChatMessage)\
        .filter(ChatMessage.user_id == user_id)\
        .count() 