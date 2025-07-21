from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.orm import Session
from typing import List
from database import get_db
from schemas.etf import (
    ETF, UserETFUpdate, InvestmentSettingsUpdate, InvestmentSettingsResponse, UserETFResponse
)
from crud.etf import (
    get_all_etfs, update_user_etf,
    get_user_settings, create_user_settings, update_user_settings,
    get_user_etfs,
)
from crud.user import get_user_by_userId
from utils.auth import get_current_user
import httpx, json

router = APIRouter()

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
    etfs = get_user_etfs(db, user_id)
    return InvestmentSettingsResponse(settings=settings, etfs=etfs)

# 투자 설정 생성/수정
@router.put("/users/me/settings", response_model=InvestmentSettingsResponse)
async def upsert_my_settings(
    settings: InvestmentSettingsUpdate,
    current_user: str = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    user = get_user_by_userId(db, current_user)
    if not user:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="사용자를 찾을 수 없습니다.")
    
    user_id = getattr(user, 'id')
    existing_settings = get_user_settings(db, user_id)

    etf_symbols = settings.etf_symbols

    try:
        async with httpx.AsyncClient() as client:
            response = await client.post("http://localhost:8001/persona", 
            json={
                "name": user.name,
                "invest_type": settings.risk_level,
                "interest": etf_symbols
            })
            persona = response.json()["persona"]
            settings.persona = persona
    except Exception as e:
        raise HTTPException(status_code=status.HTTP_500_INTERNAL_SERVER_ERROR, detail=str(e))
    
    if existing_settings:
        # 기존 설정이 있으면 수정
        updated_settings = update_user_settings(db, user_id, settings)
        if not updated_settings:
            raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="설정을 찾을 수 없습니다.")
        return InvestmentSettingsResponse(settings=updated_settings)
    else:
        new_settings = create_user_settings(db, user_id, settings)
        return InvestmentSettingsResponse(settings=new_settings)

