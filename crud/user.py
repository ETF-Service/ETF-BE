from sqlalchemy.orm import Session
from models.user import User
from utils.security import hash_password, verify_password
from schemas.user import UserCreate

def get_user_by_userId(db: Session, user_id: str):
    return db.query(User).filter(User.user_id == user_id).first()

def get_user_by_email(db: Session, email: str):
    return db.query(User).filter(User.email == email).first()

def create_user(db: Session, user: UserCreate):
    hashed_pw = hash_password(user.password)
    db_user = User(
        user_id=user.user_id,
        hashed_password=hashed_pw,
        name=user.name,
        email=user.email
    )
    db.add(db_user)
    db.commit()
    db.refresh(db_user)
    return db_user
