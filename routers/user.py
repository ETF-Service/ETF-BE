from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session
from database import SessionLocal, Base, engine
from schemas.user import UserCreate, UserLogin
from crud.user import get_user_by_username, create_user
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

@router.post("/signup")
def signup(user: UserCreate, db: Session = Depends(get_db)):
    if get_user_by_username(db, user.username):
        raise HTTPException(status_code=400, detail="이미 존재하는 아이디입니다.")
    create_user(db, user)
    return {"message": "회원가입 성공"}

@router.post("/login")
def login(user: UserLogin, db: Session = Depends(get_db)):
    db_user = get_user_by_username(db, user.username)
    if not db_user or not verify_password(user.password, str(db_user.password)):
        raise HTTPException(status_code=400, detail="아이디 또는 비밀번호가 올바르지 않습니다.")
    
    # JWT 토큰 생성
    access_token = create_access_token(data={"sub": db_user.username})
    
    return {
        "message": "로그인 성공", 
        "name": db_user.name,
        "access_token": access_token,
        "token_type": "bearer"
    }

@router.get("/me")
def get_current_user_info(current_user: str = Depends(get_current_user), db: Session = Depends(get_db)):
    db_user = get_user_by_username(db, current_user)
    if not db_user:
        raise HTTPException(status_code=404, detail="사용자를 찾을 수 없습니다.")
    return {
        "username": db_user.username,
        "name": db_user.name
    }
