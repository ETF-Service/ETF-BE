from sqlalchemy.orm import Session
from models.user import User
from utils.security import hash_password, verify_password
from schemas.user import UserCreate

def get_user_by_username(db: Session, username: str):
    return db.query(User).filter(User.username == username).first()

def create_user(db: Session, user: UserCreate):
    hashed_pw = hash_password(user.password)
    db_user = User(username=user.username, password=hashed_pw, name=user.name)
    db.add(db_user)
    db.commit()
    db.refresh(db_user)
    return db_user
