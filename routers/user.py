from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session
from database import SessionLocal, Base, engine
from schemas.user import UserCreate, UserLogin
from crud.user import get_user_by_username, create_user
from utils.security import verify_password
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
    return {"message": "로그인 성공", "name": db_user.name}
