from sqlalchemy.orm import Session, joinedload
from sqlalchemy.exc import SQLAlchemyError
from typing import List, Optional
from models.etf import ETF, InvestmentETFSettings
from models.user import InvestmentSettings
from schemas.etf import InvestmentSettingsUpdate, ETFInvestmentSettingBase, ETFInvestmentSettingUpdate

# ETF 관련 CRUD
def get_all_etfs(db: Session) -> List[ETF]:
    """모든 ETF 목록 조회"""
    try:
        return db.query(ETF).all()
    except SQLAlchemyError as e:
        db.rollback()
        raise Exception(f"ETF 목록 조회 실패: {str(e)}")

def get_etf_by_symbol(db: Session, symbol: str) -> Optional[ETF]:
    """심볼로 ETF 조회"""
    try:
        return db.query(ETF).filter(ETF.symbol == symbol).first()
    except SQLAlchemyError as e:
        db.rollback()
        raise Exception(f"ETF 조회 실패: {str(e)}")

def get_etf_by_id(db: Session, id: int) -> Optional[ETF]:
    """ID로 ETF 조회"""
    try:
        return db.query(ETF).filter(ETF.id == id).first()
    except SQLAlchemyError as e:
        db.rollback()
        raise Exception(f"ETF 조회 실패: {str(e)}")

def get_etfs_by_setting_id(db: Session, setting_id: int) -> List[ETF]:
    """사용자의 ETF 목록 조회 (최적화됨)"""
    try:
        investment_etfs = db.query(InvestmentETFSettings).options(
            joinedload(InvestmentETFSettings.etf)
        ).filter(InvestmentETFSettings.setting_id == setting_id).all()
        return [investment_etf.etf for investment_etf in investment_etfs]
    except SQLAlchemyError as e:
        db.rollback()
        raise Exception(f"사용자 ETF 목록 조회 실패: {str(e)}")

def get_investment_etf_settings_by_setting_id(db: Session, setting_id: int) -> List[InvestmentETFSettings]:
    """사용자의 투자 ETF 목록 조회"""
    try:
        return db.query(InvestmentETFSettings).filter(InvestmentETFSettings.setting_id == setting_id).all()
    except SQLAlchemyError as e:
        db.rollback()
        raise Exception(f"투자 ETF 목록 조회 실패: {str(e)}")

def get_investment_etf_settings_by_user_id(db: Session, user_id: int) -> List[InvestmentETFSettings]:
    """사용자의 ETF 설정 목록 조회"""
    try:
        # 사용자의 투자 설정 조회
        user_settings = get_user_settings(db, user_id)
        if not user_settings:
            return []
        
        # 해당 설정의 ETF 목록 조회
        return get_investment_etf_settings_by_setting_id(db, user_settings.id)
    except SQLAlchemyError as e:
        db.rollback()
        raise Exception(f"사용자 ETF 설정 조회 실패: {str(e)}")

def delete_investment_etf_settings_by_setting_id(db: Session, setting_id: int) -> List[InvestmentETFSettings]:
    """사용자의 ETF 삭제 (트랜잭션 안전)"""
    try:
        db_etfs = get_investment_etf_settings_by_setting_id(db, setting_id)
        for db_etf in db_etfs:
            db.delete(db_etf)
        # commit은 호출하는 함수에서 처리
        return get_investment_etf_settings_by_setting_id(db, setting_id)
    except SQLAlchemyError as e:
        db.rollback()
        raise Exception(f"ETF 삭제 실패: {str(e)}")

def update_investment_etf_settings(db: Session, setting_id: int, settings: InvestmentSettingsUpdate) -> List[ETF]:
    """사용자 ETF 업데이트 (기본 투자 설정 포함)"""
    try:
        if not settings.etf_symbols:
            return get_etfs_by_setting_id(db, setting_id)
        
        # 기존 ETF 삭제
        delete_investment_etf_settings_by_setting_id(db, setting_id)	
        
        # 새로운 ETF 추가 (기본 투자 설정으로)
        invalid_symbols = []
        for etf_symbol in settings.etf_symbols:
            etf = get_etf_by_symbol(db, etf_symbol)
            if not etf:
                invalid_symbols.append(etf_symbol)
                continue
            # 기본 투자 설정으로 ETF 생성
            create_user_etf(
                db, 
                setting_id, 
                etf.id,
                cycle="monthly",    # 기본값: 월간
                day=1,              # 기본값: 1일
                amount=10.0         # 기본값: 10만원
            )
        
        # 유효하지 않은 심볼이 있으면 경고 (하지만 전체 트랜잭션은 성공)
        if invalid_symbols:
            print(f"경고: 유효하지 않은 ETF 심볼들: {invalid_symbols}")
        
        return get_etfs_by_setting_id(db, setting_id)
    except SQLAlchemyError as e:
        db.rollback()
        raise Exception(f"ETF 업데이트 실패: {str(e)}")

def create_user_etf(db: Session, setting_id: int, etf_id: int, cycle: str = "monthly", day: int = 1, amount: float = 10.0) -> InvestmentETFSettings:
    """사용자 ETF 생성 (기본 투자 설정 포함)"""
    try:
        db_etf = InvestmentETFSettings(
            setting_id=setting_id,
            etf_id=etf_id,
            cycle=cycle,      # 기본값: monthly
            day=day,          # 기본값: 1일
            amount=amount     # 기본값: 10만원
        )
        db.add(db_etf)
        db.flush()  # ID 생성을 위해 flush
        return db_etf
    except SQLAlchemyError as e:
        db.rollback()
        raise Exception(f"ETF 생성 실패: {str(e)}")
    
# 투자 설정 관련 CRUD
def get_user_settings(db: Session, user_id: int) -> Optional[InvestmentSettings]:
    """사용자 투자 설정 조회"""
    try:
        return db.query(InvestmentSettings).filter(InvestmentSettings.user_id == user_id).first()
    except SQLAlchemyError as e:
        db.rollback()
        raise Exception(f"투자 설정 조회 실패: {str(e)}")

def create_user_settings(db: Session, user_id: int, settings: InvestmentSettingsUpdate) -> InvestmentSettings:
    """사용자 투자 설정 생성"""
    try:
        db_settings = InvestmentSettings(
            user_id=user_id,
            risk_level=settings.risk_level,
            api_key=settings.api_key,
            model_type=settings.model_type,
            persona=settings.persona
        )
        db.add(db_settings)
        db.flush()  # ID 생성을 위해 flush
        
        # ETF 설정
        if settings.etf_symbols:
            update_investment_etf_settings(db, db_settings.id, settings)
        
        return db_settings
    except SQLAlchemyError as e:
        db.rollback()
        raise Exception(f"투자 설정 생성 실패: {str(e)}")

def update_user_settings(db: Session, user_id: int, settings: InvestmentSettingsUpdate) -> Optional[InvestmentSettings]:
    """사용자 투자 설정 업데이트"""
    try:
        db_settings = get_user_settings(db, user_id)
        if not db_settings:
            return None
        
        # 업데이트할 필드만 처리
        update_data = settings.model_dump(exclude_unset=True, exclude={'etf_symbols'})
        for field, value in update_data.items():
            setattr(db_settings, field, value)
        
        # ETF 설정 업데이트
        if settings.etf_symbols is not None:
            update_investment_etf_settings(db, db_settings.id, settings)
        
        return db_settings
    except SQLAlchemyError as e:
        db.rollback()
        raise Exception(f"투자 설정 업데이트 실패: {str(e)}")

def get_user_investment_settings(db: Session, user_id: int) -> List[InvestmentSettings]:
    """사용자의 모든 투자 설정 조회"""
    try:
        return db.query(InvestmentSettings).filter(InvestmentSettings.user_id == user_id).all()
    except SQLAlchemyError as e:
        db.rollback()
        raise Exception(f"투자 설정 목록 조회 실패: {str(e)}")

# 초기 ETF 데이터 생성
def create_initial_etfs(db: Session) -> None:
    """초기 ETF 데이터 생성"""
    try:
        etfs_data = [
            {"symbol": "SPY", "name": "미국 S&P500", "description": "미국 대형주 지수 추종 ETF"},
            {"symbol": "QQQ", "name": "미국 나스닥", "description": "미국 기술주 지수 추종 ETF"},
            {"symbol": "EWY", "name": "한국", "description": "한국 주식 시장 ETF"},
            {"symbol": "EWJ", "name": "일본", "description": "일본 주식 시장 ETF"},
            {"symbol": "MCHI", "name": "중국", "description": "중국 주식 시장 ETF"},
            {"symbol": "VGK", "name": "유럽", "description": "유럽 주식 시장 ETF"},
        ]
        
        created_count = 0
        for etf_data in etfs_data:
            existing_etf = get_etf_by_symbol(db, etf_data["symbol"])
            if not existing_etf:
                db_etf = ETF(**etf_data)
                db.add(db_etf)
                created_count += 1
        
        if created_count > 0:
            print(f"✅ {created_count}개의 ETF 데이터가 생성되었습니다.")
        else:
            print("ℹ️ 모든 ETF 데이터가 이미 존재합니다.")
            
    except SQLAlchemyError as e:
        db.rollback()
        raise Exception(f"초기 ETF 데이터 생성 실패: {str(e)}") 

# === [추가] ETF별 개별 투자 설정 CRUD ===
def get_etf_investment_settings(db: Session, setting_id: int):
    """특정 투자 설정에 속한 모든 ETF별 투자 설정 조회"""
    try:
        return db.query(InvestmentETFSettings).filter(InvestmentETFSettings.setting_id == setting_id).all()
    except SQLAlchemyError as e:
        db.rollback()
        raise Exception(f"ETF별 투자 설정 목록 조회 실패: {str(e)}")

def get_etf_investment_setting(db: Session, setting_id: int, etf_symbol: str):
    """특정 ETF별 투자 설정 단건 조회 (심볼 기준)"""
    try:
        etf = get_etf_by_symbol(db, etf_symbol)
        if not etf:
            return None
        return db.query(InvestmentETFSettings).filter(
            InvestmentETFSettings.setting_id == setting_id,
            InvestmentETFSettings.etf_id == etf.id
        ).first()
    except SQLAlchemyError as e:
        db.rollback()
        raise Exception(f"ETF별 투자 설정 단건 조회 실패: {str(e)}")

def upsert_etf_investment_settings(db: Session, setting_id: int, etf_settings: list[ETFInvestmentSettingBase]):
    """ETF별 투자 설정 일괄 저장/수정 (전체 교체)"""
    try:
        # 기존 데이터 삭제
        db.query(InvestmentETFSettings).filter(InvestmentETFSettings.setting_id == setting_id).delete()
        db.flush()
        # 새 데이터 추가
        for setting in etf_settings:
            etf = get_etf_by_symbol(db, setting.symbol)
            if not etf:
                continue
            db_etf = InvestmentETFSettings(
                setting_id=setting_id,
                etf_id=etf.id,
                cycle=setting.cycle,
                day=setting.day,
                amount=setting.amount
            )
            db.add(db_etf)
        db.flush()
        return get_etf_investment_settings(db, setting_id)
    except SQLAlchemyError as e:
        db.rollback()
        raise Exception(f"ETF별 투자 설정 저장 실패: {str(e)}")

def update_etf_investment_setting(db: Session, setting_id: int, etf_symbol: str, update: ETFInvestmentSettingUpdate):
    """ETF별 투자 설정 단건 수정"""
    try:
        etf_setting = get_etf_investment_setting(db, setting_id, etf_symbol)
        if not etf_setting:
            return None
        if update.cycle is not None:
            etf_setting.cycle = update.cycle
        if update.day is not None:
            etf_setting.day = update.day
        if update.amount is not None:
            etf_setting.amount = update.amount
        db.flush()
        return etf_setting
    except SQLAlchemyError as e:
        db.rollback()
        raise Exception(f"ETF별 투자 설정 수정 실패: {str(e)}")

def delete_etf_investment_setting(db: Session, setting_id: int, etf_symbol: str):
    """ETF별 투자 설정 단건 삭제"""
    try:
        etf_setting = get_etf_investment_setting(db, setting_id, etf_symbol)
        if not etf_setting:
            return False
        db.delete(etf_setting)
        db.flush()
        return True
    except SQLAlchemyError as e:
        db.rollback()
        raise Exception(f"ETF별 투자 설정 삭제 실패: {str(e)}") 
