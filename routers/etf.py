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
    get_user_etfs, get_user_investment_settings,
)
from crud.user import get_user_by_userId
from utils.auth import get_current_user
import httpx
import logging

# 로거 설정
logger = logging.getLogger(__name__)

router = APIRouter()

# ETF 목록 조회
@router.get("/etfs", response_model=List[ETF])
def get_etfs(db: Session = Depends(get_db)):
    """모든 ETF 목록 조회"""
    try:
        return get_all_etfs(db)
    except Exception as e:
        logger.error(f"ETF 목록 조회 실패: {str(e)}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="ETF 목록 조회에 실패했습니다."
        )

# 내 투자 설정 조회
@router.get("/users/me/settings", response_model=InvestmentSettingsResponse)
def get_my_investment_settings(
    current_user: str = Depends(get_current_user), 
    db: Session = Depends(get_db)
):
    """사용자의 투자 설정 조회"""
    try:
        user = get_user_by_userId(db, current_user)
        if not user:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND, 
                detail="사용자를 찾을 수 없습니다."
            )
        
        user_id = user.id
        settings = get_user_settings(db, user_id)
        
        if not settings:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND, 
                detail="투자 설정을 찾을 수 없습니다."
            )
        
        etfs = get_user_etfs(db, settings.id)
        return InvestmentSettingsResponse(settings=settings, etfs=etfs)
        
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"투자 설정 조회 실패: {str(e)}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="투자 설정 조회에 실패했습니다."
        )

# 투자 설정 생성/수정
@router.put("/users/me/settings", response_model=InvestmentSettingsResponse)
async def upsert_my_settings(
    settings: InvestmentSettingsUpdate,
    current_user: str = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    """투자 설정 생성 또는 수정"""
    try:
        # 1. 사용자 조회
        user = get_user_by_userId(db, current_user)
        if not user:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND, 
                detail="사용자를 찾을 수 없습니다."
            )
        
        user_id = user.id
        
        # 2. 페르소나 생성 (AI 서비스 호출)
        persona = None
        if settings.etf_symbols:
            try:
                async with httpx.AsyncClient(timeout=30.0) as client:
                    response = await client.post(
                        "http://localhost:8001/persona",
                        json={
                            "name": user.name,
                            "invest_type": settings.risk_level or 5,
                            "interest": settings.etf_symbols
                        }
                    )
                    response.raise_for_status()
                    persona = response.json().get("persona")
                    settings.persona = persona
                    
            except httpx.TimeoutException:
                logger.warning("AI 서비스 타임아웃 - 기본 페르소나 사용")
                settings.persona = "기본 투자 상담사"
            except Exception as e:
                logger.warning(f"AI 서비스 호출 실패 - 기본 페르소나 사용: {str(e)}")
                settings.persona = "기본 투자 상담사"
        
        # 3. 기존 설정 확인
        existing_settings = get_user_settings(db, user_id)
        
        # 4. 설정 생성 또는 수정
        if existing_settings:
            # 기존 설정 수정
            updated_settings = update_user_settings(db, user_id, settings)
            if not updated_settings:
                raise HTTPException(
                    status_code=status.HTTP_404_NOT_FOUND, 
                    detail="설정을 찾을 수 없습니다."
                )
            final_settings = updated_settings
        else:
            # 새 설정 생성
            new_settings = create_user_settings(db, user_id, settings)
            final_settings = new_settings
        
        # 5. ETF 목록 조회
        etfs = get_user_etfs(db, final_settings.id)
        
        # 6. 트랜잭션 커밋
        db.commit()
        
        logger.info(f"사용자 {user.user_id}의 투자 설정이 성공적으로 저장되었습니다.")
        return InvestmentSettingsResponse(settings=final_settings, etfs=etfs)
        
    except HTTPException:
        db.rollback()
        raise
    except Exception as e:
        db.rollback()
        logger.error(f"투자 설정 저장 실패: {str(e)}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="투자 설정 저장에 실패했습니다."
        )

# 사용자 ETF 목록 조회
@router.get("/users/me/etfs", response_model=List[ETF])
def get_my_etfs(
    current_user: str = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    """사용자의 ETF 목록 조회"""
    try:
        user = get_user_by_userId(db, current_user)
        if not user:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND, 
                detail="사용자를 찾을 수 없습니다."
            )
        
        user_id = user.id
        settings = get_user_settings(db, user_id)
        
        if not settings:
            return []
        
        return get_user_etfs(db, settings.id)
        
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"사용자 ETF 목록 조회 실패: {str(e)}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="ETF 목록 조회에 실패했습니다."
        )

