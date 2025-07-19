from sqlalchemy.orm import Session, joinedload
from typing import cast
from models.etf import ETF, UserPortfolio
from models.user import InvestmentSettings
from schemas.etf import UserPortfolioCreate, InvestmentSettingsCreate, InvestmentSettingsUpdate

# ETF 관련 CRUD
def get_all_etfs(db: Session):
    return db.query(ETF).all()

def get_etf_by_symbol(db: Session, symbol: str):
    return db.query(ETF).filter(ETF.symbol == symbol).first()

# 사용자 포트폴리오 관련 CRUD
def get_user_portfolios(db: Session, user_id: int):
    return db.query(UserPortfolio).options(
        joinedload(UserPortfolio.etf)
    ).filter(UserPortfolio.user_id == user_id).all()

def create_user_portfolio(db: Session, user_id: int, portfolio: UserPortfolioCreate):
    db_portfolio = UserPortfolio(
        user_id=user_id,
        etf_id=portfolio.etf_id,
        monthly_investment=portfolio.monthly_investment
    )
    db.add(db_portfolio)
    db.commit()
    db.refresh(db_portfolio)
    
    # etf 관계를 로드하여 반환
    return db.query(UserPortfolio).options(
        joinedload(UserPortfolio.etf)
    ).filter(UserPortfolio.id == db_portfolio.id).first()

def update_user_portfolio(db: Session, portfolio_id: int, monthly_investment: float):
    db_portfolio = db.query(UserPortfolio).filter(UserPortfolio.id == portfolio_id).first()
    if db_portfolio:
        setattr(db_portfolio, 'monthly_investment', monthly_investment)
        db.commit()
        db.refresh(db_portfolio)
        
        # etf 관계를 로드하여 반환
        return db.query(UserPortfolio).options(
            joinedload(UserPortfolio.etf)
        ).filter(UserPortfolio.id == portfolio_id).first()
    return db_portfolio

def delete_user_portfolio(db: Session, portfolio_id: int, user_id: int):
    db_portfolio = db.query(UserPortfolio).filter(
        UserPortfolio.id == portfolio_id,
        UserPortfolio.user_id == user_id
    ).first()
    if db_portfolio:
        db.delete(db_portfolio)
        db.commit()
    return db_portfolio

def delete_all_user_portfolios(db: Session, user_id: int):
    """사용자의 모든 포트폴리오 삭제"""
    db.query(UserPortfolio).filter(UserPortfolio.user_id == user_id).delete()
    db.commit()

# 투자 설정 관련 CRUD
def get_user_settings(db: Session, user_id: int):
    return db.query(InvestmentSettings).filter(InvestmentSettings.user_id == user_id).first()

def create_user_settings(db: Session, user_id: int, settings: InvestmentSettingsCreate):
    db_settings = InvestmentSettings(
        user_id=user_id,
        risk_level=settings.risk_level,
        api_key=settings.api_key,
        model_type=settings.model_type
    )
    db.add(db_settings)
    db.commit()
    db.refresh(db_settings)
    return db_settings

def update_user_settings(db: Session, user_id: int, settings: InvestmentSettingsUpdate):
    db_settings = get_user_settings(db, user_id)
    if not db_settings:
        return None
    
    update_data = settings.dict(exclude_unset=True)
    for field, value in update_data.items():
        setattr(db_settings, field, value)
    
    db.commit()
    db.refresh(db_settings)
    return db_settings

# 초기 ETF 데이터 생성
def create_initial_etfs(db: Session):
    etfs_data = [
        {"symbol": "SPY", "name": "미국 S&P500", "description": "미국 대형주 지수 추종 ETF"},
        {"symbol": "QQQ", "name": "미국 나스닥", "description": "미국 기술주 지수 추종 ETF"},
        {"symbol": "EWY", "name": "한국", "description": "한국 주식 시장 ETF"},
        {"symbol": "EWJ", "name": "일본", "description": "일본 주식 시장 ETF"},
        {"symbol": "MCHI", "name": "중국", "description": "중국 주식 시장 ETF"},
        {"symbol": "VGK", "name": "유럽", "description": "유럽 주식 시장 ETF"},
    ]
    
    for etf_data in etfs_data:
        existing_etf = get_etf_by_symbol(db, etf_data["symbol"])
        if not existing_etf:
            db_etf = ETF(**etf_data)
            db.add(db_etf)
    
    db.commit() 