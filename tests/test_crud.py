import pytest
from crud.user import get_user_by_username, create_user
from crud.etf import (
    get_all_etfs, get_user_portfolios, create_user_portfolio,
    update_user_portfolio, delete_user_portfolio, delete_all_user_portfolios,
    get_user_settings, create_user_settings, update_user_settings,
    create_initial_etfs, get_etf_by_symbol
)
from schemas.user import UserCreate
from schemas.etf import UserPortfolioCreate, InvestmentSettingsCreate, InvestmentSettingsUpdate
from models.etf import ETF

class TestUserCRUD:
    """사용자 CRUD 테스트"""
    
    def test_create_user_success(self, db_session):
        """사용자 생성 성공 테스트"""
        user_data = {
            "username": "testuser",
            "password": "testpass123",
            "name": "Test User"
        }
        user_create = UserCreate(**user_data)
        user = create_user(db_session, user_create)
        
        assert user is not None
        assert user.username == user_data["username"]
        assert user.name == user_data["name"]
        assert user.password != user_data["password"]  # 해시화됨
    
    def test_get_user_by_username_success(self, db_session):
        """사용자명으로 사용자 조회 성공 테스트"""
        user_data = {
            "username": "testuser",
            "password": "testpass123",
            "name": "Test User"
        }
        user_create = UserCreate(**user_data)
        created_user = create_user(db_session, user_create)
        
        found_user = get_user_by_username(db_session, user_data["username"])
        assert found_user is not None
        assert found_user.id == created_user.id
        assert found_user.username == user_data["username"]
    
    def test_get_user_by_username_not_found(self, db_session):
        """존재하지 않는 사용자명으로 조회 테스트"""
        found_user = get_user_by_username(db_session, "nonexistent")
        assert found_user is None

class TestETFCRUD:
    """ETF CRUD 테스트"""
    
    @pytest.fixture
    def sample_etf(self, db_session):
        """샘플 ETF 데이터"""
        etf_data = {
            "symbol": "SPY",
            "name": "미국 S&P500",
            "description": "미국 S&P 500 지수를 추종하는 ETF"
        }
        etf = ETF(**etf_data)
        db_session.add(etf)
        db_session.commit()
        db_session.refresh(etf)
        return etf
    
    @pytest.fixture
    def sample_user(self, db_session):
        """샘플 사용자 데이터"""
        user_data = {
            "username": "testuser",
            "password": "testpass123",
            "name": "Test User"
        }
        user_create = UserCreate(**user_data)
        return create_user(db_session, user_create)
    
    def test_get_all_etfs_success(self, db_session, sample_etf):
        """모든 ETF 조회 성공 테스트"""
        etfs = get_all_etfs(db_session)
        assert isinstance(etfs, list)
        assert len(etfs) >= 1
        assert any(etf.symbol == sample_etf.symbol for etf in etfs)
    
    def test_get_etf_by_symbol_success(self, db_session, sample_etf):
        """심볼로 ETF 조회 성공 테스트"""
        found_etf = get_etf_by_symbol(db_session, sample_etf.symbol)
        assert found_etf is not None
        assert found_etf.symbol == sample_etf.symbol
        assert found_etf.name == sample_etf.name
    
    def test_get_etf_by_symbol_not_found(self, db_session):
        """존재하지 않는 심볼로 ETF 조회 테스트"""
        found_etf = get_etf_by_symbol(db_session, "NONEXISTENT")
        assert found_etf is None
    
    def test_create_user_portfolio_success(self, db_session, sample_user, sample_etf):
        """사용자 포트폴리오 생성 성공 테스트"""
        portfolio_data = UserPortfolioCreate(
            etf_id=sample_etf.id,
            monthly_investment=100000.0
        )
        portfolio = create_user_portfolio(db_session, sample_user.id, portfolio_data)
        
        assert portfolio is not None
        assert portfolio.user_id == sample_user.id
        assert portfolio.etf_id == sample_etf.id
        assert portfolio.monthly_investment == 100000.0
    
    def test_get_user_portfolios_success(self, db_session, sample_user, sample_etf):
        """사용자 포트폴리오 조회 성공 테스트"""
        # 포트폴리오 생성
        portfolio_data = UserPortfolioCreate(
            etf_id=sample_etf.id,
            monthly_investment=100000.0
        )
        create_user_portfolio(db_session, sample_user.id, portfolio_data)
        
        portfolios = get_user_portfolios(db_session, sample_user.id)
        assert isinstance(portfolios, list)
        assert len(portfolios) >= 1
        assert portfolios[0].etf_id == sample_etf.id
    
    def test_get_user_portfolios_empty(self, db_session, sample_user):
        """빈 포트폴리오 조회 테스트"""
        portfolios = get_user_portfolios(db_session, sample_user.id)
        assert isinstance(portfolios, list)
        assert len(portfolios) == 0
    
    def test_update_user_portfolio_success(self, db_session, sample_user, sample_etf):
        """사용자 포트폴리오 업데이트 성공 테스트"""
        # 포트폴리오 생성
        portfolio_data = UserPortfolioCreate(
            etf_id=sample_etf.id,
            monthly_investment=100000.0
        )
        portfolio = create_user_portfolio(db_session, sample_user.id, portfolio_data)
        
        # 포트폴리오 업데이트
        updated_portfolio = update_user_portfolio(db_session, portfolio.id, 150000.0)
        assert updated_portfolio is not None
        assert updated_portfolio.monthly_investment == 150000.0
    
    def test_update_user_portfolio_not_found(self, db_session):
        """존재하지 않는 포트폴리오 업데이트 테스트"""
        updated_portfolio = update_user_portfolio(db_session, 999, 150000.0)
        assert updated_portfolio is None
    
    def test_delete_user_portfolio_success(self, db_session, sample_user, sample_etf):
        """사용자 포트폴리오 삭제 성공 테스트"""
        # 포트폴리오 생성
        portfolio_data = UserPortfolioCreate(
            etf_id=sample_etf.id,
            monthly_investment=100000.0
        )
        portfolio = create_user_portfolio(db_session, sample_user.id, portfolio_data)
        
        # 포트폴리오 삭제
        deleted_portfolio = delete_user_portfolio(db_session, portfolio.id, sample_user.id)
        assert deleted_portfolio is not None
        assert deleted_portfolio.id == portfolio.id
    
    def test_delete_user_portfolio_not_found(self, db_session, sample_user):
        """존재하지 않는 포트폴리오 삭제 테스트"""
        deleted_portfolio = delete_user_portfolio(db_session, 999, sample_user.id)
        assert deleted_portfolio is None
    
    def test_delete_all_user_portfolios_success(self, db_session, sample_user, sample_etf):
        """사용자 모든 포트폴리오 삭제 성공 테스트"""
        # 포트폴리오 생성
        portfolio_data = UserPortfolioCreate(
            etf_id=sample_etf.id,
            monthly_investment=100000.0
        )
        create_user_portfolio(db_session, sample_user.id, portfolio_data)
        
        # 모든 포트폴리오 삭제
        delete_all_user_portfolios(db_session, sample_user.id)
        
        # 삭제 확인
        portfolios = get_user_portfolios(db_session, sample_user.id)
        assert len(portfolios) == 0
    
    def test_create_user_settings_success(self, db_session, sample_user):
        """사용자 설정 생성 성공 테스트"""
        settings_data = InvestmentSettingsCreate(
            risk_level=7,
            api_key="test_api_key",
            model_type="gpt-4o"
        )
        settings = create_user_settings(db_session, sample_user.id, settings_data)
        
        assert settings is not None
        assert settings.user_id == sample_user.id
        assert settings.risk_level == 7
        assert settings.api_key == "test_api_key"
        assert settings.model_type == "gpt-4o"
    
    def test_get_user_settings_success(self, db_session, sample_user):
        """사용자 설정 조회 성공 테스트"""
        # 설정 생성
        settings_data = InvestmentSettingsCreate(
            risk_level=7,
            api_key="test_api_key",
            model_type="gpt-4o"
        )
        create_user_settings(db_session, sample_user.id, settings_data)
        
        settings = get_user_settings(db_session, sample_user.id)
        assert settings is not None
        assert settings.user_id == sample_user.id
        assert settings.risk_level == 7
    
    def test_get_user_settings_not_found(self, db_session, sample_user):
        """설정이 없는 사용자 조회 테스트"""
        settings = get_user_settings(db_session, sample_user.id)
        assert settings is None
    
    def test_update_user_settings_success(self, db_session, sample_user):
        """사용자 설정 업데이트 성공 테스트"""
        # 초기 설정 생성
        initial_settings = InvestmentSettingsCreate(
            risk_level=5,
            api_key="initial_key",
            model_type="gpt-4o"
        )
        create_user_settings(db_session, sample_user.id, initial_settings)
        
        # 설정 업데이트
        update_data = InvestmentSettingsUpdate(
            risk_level=8,
            api_key="updated_key",
            model_type="gpt-4o-mini"
        )
        updated_settings = update_user_settings(db_session, sample_user.id, update_data)
        
        assert updated_settings is not None
        assert updated_settings.risk_level == 8
        assert updated_settings.api_key == "updated_key"
        assert updated_settings.model_type == "gpt-4o-mini"
    
    def test_update_user_settings_not_found(self, db_session, sample_user):
        """설정이 없는 사용자 업데이트 테스트"""
        update_data = InvestmentSettingsUpdate(
            risk_level=8,
            api_key="updated_key",
            model_type="gpt-4o-mini"
        )
        updated_settings = update_user_settings(db_session, sample_user.id, update_data)
        assert updated_settings is None
    
    def test_create_initial_etfs_success(self, db_session):
        """초기 ETF 데이터 생성 성공 테스트"""
        # 기존 ETF 데이터 삭제
        db_session.query(ETF).delete()
        db_session.commit()
        
        # 초기 ETF 데이터 생성
        create_initial_etfs(db_session)
        
        # 생성 확인
        etfs = get_all_etfs(db_session)
        assert len(etfs) > 0 