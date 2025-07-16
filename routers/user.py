from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.orm import Session
from database import SessionLocal, Base, engine
from schemas.user import UserCreate, UserLogin
from crud.user import get_user_by_userId, create_user
from utils.security import verify_password
from utils.auth import create_access_token, get_current_user
from models import user as user_model

user_model.Base.metadata.create_all(bind=engine)

router = APIRouter()

def get_db():
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()

@router.post("/users", status_code=status.HTTP_201_CREATED)
def create_user_endpoint(user: UserCreate, db: Session = Depends(get_db)):
    if get_user_by_userId(db, user.user_id):
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="이미 존재하는 사용자입니다."
        )
    db_user = create_user(db, user)
    return {"message": "회원가입 성공", "user_id": db_user.id}

@router.post("/auth/login")
def login_endpoint(user: UserLogin, db: Session = Depends(get_db)):
    db_user = get_user_by_userId(db, user.user_id)
    if not db_user or not verify_password(user.password, str(db_user.hashed_password)):
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST, 
            detail="아이디 또는 비밀번호가 올바르지 않습니다."
        )
    access_token = create_access_token(data={"sub": db_user.user_id})
    return {
        "message": "로그인 성공", 
        "user_id": db_user.user_id,
        "name": db_user.name,
        "access_token": access_token,
        "token_type": "bearer"
    }

@router.get("/users/me")
def get_me(current_user=Depends(get_current_user)):
    return {
        "user_id": current_user.user_id,
        "name": current_user.name,
        "email": current_user.email,
        "created_at": current_user.created_at
    }
