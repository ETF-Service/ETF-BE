from sqlalchemy.orm import Session
from sqlalchemy.exc import SQLAlchemyError
from models.user import User
from utils.security import hash_password, verify_password
from schemas.user import UserCreate
from typing import Optional, List

def get_user_by_userId(db: Session, user_id: str) -> Optional[User]:
    """사용자 ID로 사용자 조회"""
    try:
        return db.query(User).filter(User.user_id == user_id).first()
    except SQLAlchemyError as e:
        db.rollback()
        raise Exception(f"사용자 조회 실패: {str(e)}")

def get_user_by_email(db: Session, email: str) -> Optional[User]:
    """이메일로 사용자 조회"""
    try:
        return db.query(User).filter(User.email == email).first()
    except SQLAlchemyError as e:
        db.rollback()
        raise Exception(f"이메일로 사용자 조회 실패: {str(e)}")

def get_user_by_id(db: Session, user_id: int) -> Optional[User]:
    """ID로 사용자 조회"""
    try:
        return db.query(User).filter(User.id == user_id).first()
    except SQLAlchemyError as e:
        db.rollback()
        raise Exception(f"사용자 ID 조회 실패: {str(e)}")

def create_user(db: Session, user: UserCreate) -> User:
    """새 사용자 생성"""
    try:
        hashed_pw = hash_password(user.password)
        db_user = User(
            user_id=user.user_id,
            hashed_password=hashed_pw,
            name=user.name,
            email=user.email
        )
        db.add(db_user)
        db.flush()  # ID 생성을 위해 flush
        return db_user
    except SQLAlchemyError as e:
        db.rollback()
        raise Exception(f"사용자 생성 실패: {str(e)}")

def update_user(db: Session, user_id: int, **kwargs) -> Optional[User]:
    """사용자 정보 업데이트"""
    try:
        db_user = get_user_by_id(db, user_id)
        if not db_user:
            return None
        
        for field, value in kwargs.items():
            if hasattr(db_user, field):
                setattr(db_user, field, value)
        
        return db_user
    except SQLAlchemyError as e:
        db.rollback()
        raise Exception(f"사용자 업데이트 실패: {str(e)}")

def delete_user(db: Session, user_id: int) -> bool:
    """사용자 삭제"""
    try:
        db_user = get_user_by_id(db, user_id)
        if not db_user:
            return False
        
        db.delete(db_user)
        return True
    except SQLAlchemyError as e:
        db.rollback()
        raise Exception(f"사용자 삭제 실패: {str(e)}")

def get_all_users(db: Session, skip: int = 0, limit: int = 100) -> List[User]:
    """모든 사용자 조회 (페이지네이션)"""
    try:
        return db.query(User).offset(skip).limit(limit).all()
    except SQLAlchemyError as e:
        db.rollback()
        raise Exception(f"사용자 목록 조회 실패: {str(e)}")

def check_user_exists(db: Session, user_id: str = None, email: str = None) -> bool:
    """사용자 존재 여부 확인"""
    try:
        if user_id:
            return db.query(User).filter(User.user_id == user_id).first() is not None
        elif email:
            return db.query(User).filter(User.email == email).first() is not None
        return False
    except SQLAlchemyError as e:
        db.rollback()
        raise Exception(f"사용자 존재 확인 실패: {str(e)}")

def update_user_password(db: Session, user_id: int, new_password: str) -> Optional[User]:
    """사용자 비밀번호 변경"""
    try:
        db_user = get_user_by_id(db, user_id)
        if not db_user:
            return None
        
        hashed_password = hash_password(new_password)
        db_user.hashed_password = hashed_password
        
        return db_user
    except SQLAlchemyError as e:
        db.rollback()
        raise Exception(f"비밀번호 변경 실패: {str(e)}")

def verify_user_credentials(db: Session, user_id: str, password: str) -> Optional[User]:
    """사용자 인증 정보 확인"""
    try:
        db_user = get_user_by_userId(db, user_id)
        if not db_user:
            return None
        
        if verify_password(password, str(db_user.hashed_password)):
            return db_user
        
        return None
    except SQLAlchemyError as e:
        db.rollback()
        raise Exception(f"사용자 인증 실패: {str(e)}")
