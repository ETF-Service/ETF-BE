# ETF 백엔드 테스트 가이드

## 📋 개요

이 디렉토리는 ETF 백엔드 API의 테스트 코드를 포함합니다.

## 🚀 테스트 실행

### 1. 의존성 설치
```bash
pip install -r requirements.txt
```

### 2. 테스트 실행
```bash
# 모든 테스트 실행
python run_tests.py

# 또는 pytest 직접 실행
pytest tests/ -v

# 커버리지와 함께 실행
pytest tests/ -v --cov=. --cov-report=html
```

### 3. 특정 테스트 실행
```bash
# 특정 파일의 테스트만 실행
pytest tests/test_user.py -v

# 특정 테스트 함수만 실행
pytest tests/test_user.py::TestUserAPI::test_signup_success -v
```

## 📁 테스트 구조

```
tests/
├── __init__.py          # 테스트 패키지 초기화
├── conftest.py          # pytest 설정 및 공통 fixtures
├── test_user.py         # 사용자 API 테스트
├── test_chat.py         # 채팅 API 테스트
└── test_etf.py          # ETF API 테스트
```

## 🧪 테스트 종류

### 1. 사용자 API 테스트 (`test_user.py`)
- 회원가입 성공/실패 케이스
- 로그인 성공/실패 케이스
- 사용자 정보 조회
- 인증 토큰 검증

### 2. 채팅 API 테스트 (`test_chat.py`)
- 메시지 전송 성공/실패 케이스
- 스트리밍 응답 테스트
- 인증되지 않은 요청 처리

### 3. ETF API 테스트 (`test_etf.py`)
- 포트폴리오 조회/생성/삭제
- 투자 설정 관리
- ETF 데이터 처리

## 🔧 테스트 설정

### Fixtures
- `client`: FastAPI 테스트 클라이언트
- `db_session`: 테스트용 데이터베이스 세션
- `test_user`: 테스트용 사용자 데이터
- `authenticated_client`: 인증된 테스트 클라이언트

### 데이터베이스
- 테스트용 인메모리 SQLite 데이터베이스 사용
- 각 테스트마다 데이터베이스 초기화

## 📊 커버리지

테스트 커버리지는 다음 명령으로 확인할 수 있습니다:

```bash
pytest --cov=. --cov-report=html
```

결과는 `htmlcov/` 디렉토리에 생성됩니다.

## 🐛 문제 해결

### 1. Import 오류
```bash
# PYTHONPATH 설정
export PYTHONPATH="${PYTHONPATH}:$(pwd)"
```

### 2. 데이터베이스 오류
```bash
# 데이터베이스 파일 삭제 후 재생성
rm -f app.db
python -c "from database import Base, engine; Base.metadata.create_all(bind=engine)"
```

### 3. 의존성 오류
```bash
# 가상환경 재생성
python -m venv venv
source venv/bin/activate  # Windows: venv\Scripts\activate
pip install -r requirements.txt
```

## 📝 테스트 작성 가이드

### 새로운 테스트 추가
1. `tests/test_[기능명].py` 파일 생성
2. 테스트 클래스 정의
3. 테스트 함수 작성
4. 필요한 fixtures 사용

### 테스트 네이밍
- 파일명: `test_[기능명].py`
- 클래스명: `Test[기능명]API`
- 함수명: `test_[시나리오]_[예상결과]`

### 예시
```python
def test_user_signup_success(self, client, test_user):
    """회원가입 성공 테스트"""
    response = client.post("/signup", json=test_user)
    assert response.status_code == status.HTTP_200_OK
    assert response.json()["message"] == "회원가입 성공"
``` 