from sqlalchemy.orm import Session, joinedload
from models.etf import ETF, InvestmentEtf
from models.user import InvestmentSettings
from schemas.etf import UserETFUpdate, InvestmentSettingsUpdate

# ETF 관련 CRUD
def get_all_etfs(db: Session):
    return db.query(ETF).all()

def get_etf_by_symbol(db: Session, symbol: str):
    return db.query(ETF).filter(ETF.symbol == symbol).first()

def get_user_etfs(db: Session, setting_id: int):
    etfs = db.query(InvestmentEtf).options(
        joinedload(InvestmentEtf.etf)
    ).filter(InvestmentEtf.setting_id == setting_id).all()
    return [etf.etf for etf in etfs]

def get_user_etf_by_etf_id(db: Session, etf_id: int):
    return db.query(InvestmentEtf).filter(InvestmentEtf.etf_id == etf_id).first()

def get_user_investment_etfs(db: Session, setting_id: int):
    return db.query(InvestmentEtf).filter(InvestmentEtf.setting_id == setting_id).all()

def delete_user_etf(db: Session, setting_id: int):
    db_etfs = get_user_investment_etfs(db, setting_id)
    for db_etf in db_etfs:
        db.delete(db_etf)
    db.commit()
    return get_user_investment_etfs(db, setting_id)  

def update_user_etf(db: Session, setting_id: int, settings: InvestmentSettingsUpdate):
    if settings.etf_symbols:
        delete_user_etf(db, setting_id)
        for etf_symbol in settings.etf_symbols:
            etf = get_etf_by_symbol(db, etf_symbol)
            if not etf:
                continue
            etf_id = getattr(etf, 'id')
            create_user_etf(db, setting_id, etf_id)
    return get_user_etfs(db, setting_id)

def create_user_etf(db: Session, setting_id: int, etf_id: int):
    db_etf = InvestmentEtf(
        setting_id=setting_id,
        etf_id=etf_id,
    )
    db.add(db_etf)
    db.commit()
    db.refresh(db_etf)
    return db_etf
    
# 투자 설정 관련 CRUD
def get_user_settings(db: Session, user_id: int):
    return db.query(InvestmentSettings).filter(InvestmentSettings.user_id == user_id).first()

def create_user_settings(db: Session, user_id: int, settings: InvestmentSettingsUpdate):
    db_settings = InvestmentSettings(
        user_id=user_id,
        risk_level=settings.risk_level,
        api_key=settings.api_key,
        model_type=settings.model_type,
        monthly_investment=settings.monthly_investment,
        persona=settings.persona
    )
    db.add(db_settings)
    db.commit()
    db.refresh(db_settings)
    setting_id = getattr(db_settings, 'id')
    update_user_etf(db, setting_id, settings)
    return db_settings

def update_user_settings(db: Session, user_id: int, settings: InvestmentSettingsUpdate):
    db_settings = get_user_settings(db, user_id)
    if not db_settings:
        return None
    
    update_data = settings.model_dump(exclude_unset=True)
    for field, value in update_data.items():
        setattr(db_settings, field, value)
    
    db.commit()
    db.refresh(db_settings)
    setting_id = getattr(db_settings, 'id')
    update_user_etf(db, setting_id, settings)
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
