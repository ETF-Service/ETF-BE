from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.orm import Session
from typing import List
from database import SessionLocal
from models import etf as etf_model
from schemas.etf import (
    ETF, UserETF, UserETFUpdate, 
    InvestmentSettings, InvestmentSettingsCreate, InvestmentSettingsUpdate,
    UserPortfolioResponse
)
from crud.etf import (
    get_all_etfs, get_user_etfs, update_user_etf,
    get_user_settings, create_user_settings, update_user_settings,
    create_initial_etfs
)
from crud.user import get_user_by_userId
from utils.auth import get_current_user

# 데이터베이스 테이블 생성
etf_model.Base.metadata.create_all(bind=SessionLocal().bind)

router = APIRouter()

def get_db():
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()

# ETF 목록 조회
@router.get("/etfs", response_model=List[ETF])
def get_etfs(db: Session = Depends(get_db)):
    return get_all_etfs(db)

# 내 정보 가져오기
@router.get("/users/me/settings", response_model=UserPortfolioResponse)
def get_my_investment_settings(current_user: str = Depends(get_current_user), db: Session = Depends(get_db)):
    user = get_user_by_userId(db, current_user)
    if not user:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="사용자를 찾을 수 없습니다.")
    user_id = getattr(user, 'id')
    settings = get_user_settings(db, user_id)
    setting_id = getattr(settings, 'id')
    etfs = get_user_etfs(db, setting_id)
    return UserPortfolioResponse(settings=settings, etfs=etfs)

# 투자 설정 생성
@router.post("/users/me/settings", response_model=InvestmentSettings)
def create_my_settings(
    settings: InvestmentSettingsCreate,
    current_user: str = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    user = get_user_by_userId(db, current_user)
    if not user:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="사용자를 찾을 수 없습니다.")
    user_id = getattr(user, 'id')
    existing_settings = get_user_settings(db, user_id)
    if existing_settings:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="이미 설정이 존재합니다.")
    return create_user_settings(db, user_id, settings)

# 투자 설정 수정
@router.put("/users/me/settings", response_model=InvestmentSettings)
def update_my_settings(
    settings: InvestmentSettingsUpdate,
    current_user: str = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    user = get_user_by_userId(db, current_user)
    if not user:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="사용자를 찾을 수 없습니다.")
    user_id = getattr(user, 'id')
    updated_settings = update_user_settings(db, user_id, settings)
    if not updated_settings:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="설정을 찾을 수 없습니다.")
    return updated_settings

# ETF 정보 수정
@router.put("/users/me/etf", response_model=UserETF)
def update_my_etf(
    etf: UserETFUpdate,
    current_user: str = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    user = get_user_by_userId(db, current_user)
    if not user:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="사용자를 찾을 수 없습니다.")
    user_id = getattr(user, 'id')
    setting = get_user_settings(db, user_id)
    setting_id = getattr(setting, 'id')
    return update_user_etf(db, setting_id, etf)

# ETF 데이터 초기화
@router.post("/init-etfs")
def initialize_etfs(db: Session = Depends(get_db)):
    try:
        create_initial_etfs(db)
        return {"message": "ETF 데이터가 초기화되었습니다."}
    except Exception as e:
        return {"message": f"ETF 데이터 초기화 중 오류: {str(e)}"} 