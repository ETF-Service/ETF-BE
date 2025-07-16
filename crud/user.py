from sqlalchemy.orm import Session
from models.user import User
from utils.security import hash_password, verify_password
from schemas.user import UserCreate

def get_user_by_userId(db: Session, userId: str):
    return db.query(User).filter(User.userId == userId).first()

def create_user(db: Session, user: UserCreate):
    hashed_pw = hash_password(user.password)
    db_user = User(
        userId=user.userId,
        hashed_password=hashed_pw,
        name=user.name,
        email=user.email
    )
    db.add(db_user)
    db.commit()
    db.refresh(db_user)
    return db_user
