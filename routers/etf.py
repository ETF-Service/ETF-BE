from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.orm import Session
from typing import List
from database import SessionLocal
from models import etf as etf_model
from schemas.etf import (
    ETF, UserPortfolio, UserPortfolioCreate, 
    InvestmentSettings, InvestmentSettingsCreate, InvestmentSettingsUpdate,
    UserPortfolioResponse
)
from crud.etf import (
    get_all_etfs, get_user_portfolios, create_user_portfolio,
    update_user_portfolio, delete_user_portfolio, delete_all_user_portfolios,
    get_user_settings, create_user_settings, update_user_settings,
    create_initial_etfs
)
from crud.user import get_user_by_username
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

@router.get("/etfs", response_model=List[ETF])
def get_etfs(db: Session = Depends(get_db)):
    """모든 ETF 목록 조회"""
    return get_all_etfs(db)

@router.get("/portfolio", response_model=UserPortfolioResponse)
def get_portfolio(current_user: str = Depends(get_current_user), db: Session = Depends(get_db)):
    """사용자의 포트폴리오 및 설정 조회"""
    user = get_user_by_username(db, current_user)
    if not user:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="사용자를 찾을 수 없습니다.")
    
    user_id = getattr(user, 'id')
    portfolios = get_user_portfolios(db, user_id)
    settings = get_user_settings(db, user_id)
    
    return UserPortfolioResponse(portfolios=portfolios, settings=settings)

@router.post("/portfolio", response_model=UserPortfolio)
def add_portfolio(
    portfolio: UserPortfolioCreate,
    current_user: str = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    """포트폴리오에 ETF 추가"""
    user = get_user_by_username(db, current_user)
    if not user:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="사용자를 찾을 수 없습니다.")
    
    user_id = getattr(user, 'id')
    return create_user_portfolio(db, user_id, portfolio)

@router.put("/portfolio/{portfolio_id}")
def update_portfolio(
    portfolio_id: int,
    monthly_investment: float,
    current_user: str = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    """포트폴리오 투자 금액 수정"""
    user = get_user_by_username(db, current_user)
    if not user:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="사용자를 찾을 수 없습니다.")
    
    portfolio = update_user_portfolio(db, portfolio_id, monthly_investment)
    if not portfolio:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="포트폴리오를 찾을 수 없습니다.")
    
    return {"message": "포트폴리오가 업데이트되었습니다."}

@router.delete("/portfolio/{portfolio_id}")
def delete_portfolio(
    portfolio_id: int,
    current_user: str = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    """포트폴리오에서 ETF 제거"""
    user = get_user_by_username(db, current_user)
    if not user:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="사용자를 찾을 수 없습니다.")
    
    user_id = getattr(user, 'id')
    portfolio = delete_user_portfolio(db, portfolio_id, user_id)
    if not portfolio:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="포트폴리오를 찾을 수 없습니다.")
    
    return {"message": "포트폴리오가 삭제되었습니다."}

@router.delete("/portfolio")
def delete_all_portfolios(
    current_user: str = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    """사용자의 모든 포트폴리오 삭제"""
    user = get_user_by_username(db, current_user)
    if not user:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="사용자를 찾을 수 없습니다.")
    
    user_id = getattr(user, 'id')
    delete_all_user_portfolios(db, user_id)
    
    return {"message": "모든 포트폴리오가 삭제되었습니다."}

@router.post("/settings", response_model=InvestmentSettings)
def create_settings(
    settings: InvestmentSettingsCreate,
    current_user: str = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    """투자 설정 생성"""
    user = get_user_by_username(db, current_user)
    if not user:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="사용자를 찾을 수 없습니다.")
    
    user_id = getattr(user, 'id')
    existing_settings = get_user_settings(db, user_id)
    if existing_settings:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="이미 설정이 존재합니다.")
    
    return create_user_settings(db, user_id, settings)

@router.put("/settings", response_model=InvestmentSettings)
def update_settings(
    settings: InvestmentSettingsUpdate,
    current_user: str = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    """투자 설정 수정"""
    user = get_user_by_username(db, current_user)
    if not user:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="사용자를 찾을 수 없습니다.")
    
    user_id = getattr(user, 'id')
    updated_settings = update_user_settings(db, user_id, settings)
    if not updated_settings:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="설정을 찾을 수 없습니다.")
    
    return updated_settings

@router.post("/init-etfs")
def initialize_etfs(db: Session = Depends(get_db)):
    """초기 ETF 데이터 생성 (개발용)"""
    try:
        create_initial_etfs(db)
        return {"message": "ETF 데이터가 초기화되었습니다."}
    except Exception as e:
        return {"message": f"ETF 데이터 초기화 중 오류: {str(e)}"} 