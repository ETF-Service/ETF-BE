import pytest
import asyncio
from fastapi.testclient import TestClient
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker
from sqlalchemy.pool import StaticPool

from main import app
from database import Base, get_db
from utils.auth import create_access_token

# 테스트용 데이터베이스 설정
SQLALCHEMY_DATABASE_URL = "sqlite:///:memory:"

engine = create_engine(
    SQLALCHEMY_DATABASE_URL,
    connect_args={"check_same_thread": False},
    poolclass=StaticPool,
)
TestingSessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)

@pytest.fixture(scope="session")
def event_loop():
    """이벤트 루프 fixture"""
    loop = asyncio.get_event_loop_policy().new_event_loop()
    yield loop
    loop.close()

@pytest.fixture(scope="function")
def db_session():
    """테스트용 데이터베이스 세션"""
    Base.metadata.create_all(bind=engine)
    session = TestingSessionLocal()
    try:
        yield session
    finally:
        session.close()
        Base.metadata.drop_all(bind=engine)

@pytest.fixture(scope="function")
def client(db_session):
    """테스트용 FastAPI 클라이언트"""
    def override_get_db():
        try:
            yield db_session
        finally:
            pass
    
    app.dependency_overrides[get_db] = override_get_db
    with TestClient(app) as test_client:
        yield test_client
    app.dependency_overrides.clear()

@pytest.fixture
def test_user():
    """테스트용 사용자 데이터"""
    return {
        "username": "testuser",
        "password": "testpass123",
        "name": "Test User"
    }

@pytest.fixture
def test_user_token(test_user):
    """테스트용 JWT 토큰"""
    return create_access_token(data={"sub": test_user["username"]})

@pytest.fixture
def authenticated_client(client, test_user_token):
    """인증된 테스트 클라이언트"""
    client.headers.update({"Authorization": f"Bearer {test_user_token}"})
    return client 