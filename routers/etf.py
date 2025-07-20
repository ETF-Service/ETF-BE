from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.orm import Session
from typing import List
from database import SessionLocal
from schemas.etf import (
    ETF, UserETFUpdate, 
    InvestmentSettings, InvestmentSettingsCreate, InvestmentSettingsUpdate,
    InvestmentSettingsResponse, ETFBase, UserETFResponse
)
from crud.etf import (
    get_all_etfs, update_user_etf,
    get_user_settings, create_user_settings, update_user_settings,
    get_user_etfs,
)
from crud.user import get_user_by_userId
from utils.auth import get_current_user

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
@router.get("/users/me/settings", response_model=InvestmentSettingsResponse)
def get_my_investment_settings(current_user: str = Depends(get_current_user), db: Session = Depends(get_db)):
    user = get_user_by_userId(db, current_user)
    if not user:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="사용자를 찾을 수 없습니다.")
    user_id = getattr(user, 'id')
    settings = get_user_settings(db, user_id)
    return InvestmentSettingsResponse(settings=settings)

# 투자 설정 생성
@router.post("/users/me/settings", response_model=InvestmentSettingsCreate)
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
@router.put("/users/me/settings", response_model=InvestmentSettingsUpdate)
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

# ETF 목록 조회
@router.get("/users/me/etf", response_model=UserETFResponse)
def get_my_etf(current_user: str = Depends(get_current_user), db: Session = Depends(get_db)):
    user = get_user_by_userId(db, current_user)
    if not user:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="사용자를 찾을 수 없습니다.")
    user_id = getattr(user, 'id')
    setting = get_user_settings(db, user_id)
    if not setting:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="설정을 찾을 수 없습니다.")
    setting_id = getattr(setting, 'id')
    etfs = get_user_etfs(db, setting_id)
    return UserETFResponse(etfs=etfs)

# ETF 정보 수정
@router.put("/users/me/etf", response_model=UserETFUpdate)
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
    if not setting:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="설정을 찾을 수 없습니다.")
    setting_id = getattr(setting, 'id')
    return update_user_etf(db, setting_id, etf)
