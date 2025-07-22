from sqlalchemy.orm import Session
from sqlalchemy.exc import SQLAlchemyError
from models.chat import ChatMessage
from typing import List, Optional

def save_message(db: Session, user_id: int, role: str, content: str) -> ChatMessage:
    """대화 메시지를 데이터베이스에 저장"""
    try:
        db_message = ChatMessage(
            user_id=user_id,
            role=role,
            content=content
        )
        db.add(db_message)
        db.flush()  # ID 생성을 위해 flush
        return db_message
    except SQLAlchemyError as e:
        db.rollback()
        raise Exception(f"메시지 저장 실패: {str(e)}")

def get_chat_history(db: Session, user_id: int, limit: int = 50) -> List[ChatMessage]:
    """사용자의 대화 히스토리를 조회 (최신순)"""
    try:
        return db.query(ChatMessage)\
            .filter(ChatMessage.user_id == user_id)\
            .order_by(ChatMessage.created_at.desc())\
            .limit(limit)\
            .all()
    except SQLAlchemyError as e:
        db.rollback()
        raise Exception(f"대화 히스토리 조회 실패: {str(e)}")

def get_chat_history_asc(db: Session, user_id: int, limit: int = 50) -> List[ChatMessage]:
    """사용자의 대화 히스토리를 조회 (시간순) - AI 서버용"""
    try:
        return db.query(ChatMessage)\
            .filter(ChatMessage.user_id == user_id)\
            .order_by(ChatMessage.created_at.asc())\
            .limit(limit)\
            .all()
    except SQLAlchemyError as e:
        db.rollback()
        raise Exception(f"대화 히스토리 조회 실패: {str(e)}")

def delete_chat_history(db: Session, user_id: int) -> bool:
    """사용자의 모든 대화 히스토리 삭제"""
    try:
        deleted_count = db.query(ChatMessage)\
            .filter(ChatMessage.user_id == user_id)\
            .delete()
        # commit은 호출하는 함수에서 처리
        return deleted_count > 0
    except SQLAlchemyError as e:
        db.rollback()
        raise Exception(f"대화 히스토리 삭제 실패: {str(e)}")

def get_message_count(db: Session, user_id: int) -> int:
    """사용자의 대화 메시지 개수 조회"""
    try:
        return db.query(ChatMessage)\
            .filter(ChatMessage.user_id == user_id)\
            .count()
    except SQLAlchemyError as e:
        db.rollback()
        raise Exception(f"메시지 개수 조회 실패: {str(e)}")

def get_chat_message_by_id(db: Session, message_id: int) -> Optional[ChatMessage]:
    """메시지 ID로 특정 메시지 조회"""
    try:
        return db.query(ChatMessage)\
            .filter(ChatMessage.id == message_id)\
            .first()
    except SQLAlchemyError as e:
        db.rollback()
        raise Exception(f"메시지 조회 실패: {str(e)}")

def update_message(db: Session, message_id: int, content: str) -> Optional[ChatMessage]:
    """메시지 내용 업데이트"""
    try:
        db_message = get_chat_message_by_id(db, message_id)
        if not db_message:
            return None
        
        db_message.content = content
        return db_message
    except SQLAlchemyError as e:
        db.rollback()
        raise Exception(f"메시지 업데이트 실패: {str(e)}")

def delete_message(db: Session, message_id: int) -> bool:
    """특정 메시지 삭제"""
    try:
        db_message = get_chat_message_by_id(db, message_id)
        if not db_message:
            return False
        
        db.delete(db_message)
        return True
    except SQLAlchemyError as e:
        db.rollback()
        raise Exception(f"메시지 삭제 실패: {str(e)}")

def get_recent_messages_by_role(db: Session, user_id: int, role: str, limit: int = 10) -> List[ChatMessage]:
    """특정 역할의 최근 메시지 조회"""
    try:
        return db.query(ChatMessage)\
            .filter(ChatMessage.user_id == user_id, ChatMessage.role == role)\
            .order_by(ChatMessage.created_at.desc())\
            .limit(limit)\
            .all()
    except SQLAlchemyError as e:
        db.rollback()
        raise Exception(f"역할별 메시지 조회 실패: {str(e)}") 