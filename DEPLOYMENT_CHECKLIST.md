# ETF Backend Railway 배포 체크리스트

## 🚀 배포 전 준비사항

### 1. 코드 준비
- [ ] 모든 변경사항이 Git에 커밋되었는지 확인
- [ ] 로컬에서 애플리케이션이 정상 작동하는지 테스트
- [ ] 데이터베이스 마이그레이션이 완료되었는지 확인

### 2. Railway 계정 및 CLI
- [ ] Railway 계정 생성 완료
- [ ] Railway CLI 설치: `npm install -g @railway/cli`
- [ ] Railway CLI 로그인: `railway login`

### 3. 프로젝트 초기화
- [ ] Railway 프로젝트 초기화: `railway init`
- [ ] PostgreSQL 데이터베이스 추가: `railway add`

## 🔧 환경변수 설정

### 필수 환경변수 (Railway에서 자동 설정)
- [ ] `DATABASE_URL`: PostgreSQL 연결 URL
- [ ] `PORT`: 애플리케이션 포트

### 선택적 환경변수 (수동 설정 필요)
- [ ] `SECRET_KEY`: JWT 토큰 암호화 키
- [ ] `ALGORITHM`: JWT 알고리즘 (기본값: HS256)
- [ ] `ACCESS_TOKEN_EXPIRE_MINUTES`: 토큰 만료 시간 (기본값: 30)
- [ ] `OPENAI_API_KEY`: OpenAI API 키 (AI 기능 사용 시)

## 📁 파일 확인

### 배포 필수 파일
- [ ] `Dockerfile`: Docker 이미지 빌드 설정
- [ ] `railway.json`: Railway 배포 설정
- [ ] `requirements.txt`: Python 의존성 목록
- [ ] `.dockerignore`: Docker 빌드 제외 파일 목록

### 애플리케이션 파일
- [ ] `main.py`: FastAPI 애플리케이션 진입점
- [ ] `database.py`: 데이터베이스 연결 설정
- [ ] 모든 라우터 파일들 (`routers/` 디렉토리)
- [ ] 모든 모델 파일들 (`models/` 디렉토리)
- [ ] 모든 스키마 파일들 (`schemas/` 디렉토리)

## 🧪 로컬 테스트

### Docker 빌드 테스트
```bash
# Docker 이미지 빌드
docker build -t etf-backend .

# Docker 컨테이너 실행
docker run -p 8000:8000 etf-backend

# 헬스체크 확인
curl http://localhost:8000/health
```

### 애플리케이션 테스트
```bash
# 의존성 설치
pip install -r requirements.txt

# 애플리케이션 실행
uvicorn main:app --host 0.0.0.0 --port 8000

# API 테스트
python test_railway_deployment.py http://localhost:8000
```

## 🚀 배포 실행

### 1. 자동 배포 스크립트 사용
```bash
# 배포 스크립트 실행
./deploy_to_railway.sh
```

### 2. 수동 배포
```bash
# Railway에 배포
railway up

# 배포 상태 확인
railway status

# 로그 확인
railway logs
```

## ✅ 배포 후 확인

### 1. 헬스체크
```bash
# 배포 URL 확인
railway status

# 헬스체크 실행
curl https://your-app-name.railway.app/health
```

### 2. API 테스트
```bash
# 전체 API 테스트
python test_railway_deployment.py https://your-app-name.railway.app
```

### 3. 로그 모니터링
```bash
# 실시간 로그 확인
railway logs --follow

# 최근 로그 확인
railway logs --tail 50
```

## 🔍 문제 해결

### 빌드 실패
- [ ] Dockerfile 문법 오류 확인
- [ ] requirements.txt 의존성 충돌 확인
- [ ] 시스템 의존성 설치 확인

### 런타임 오류
- [ ] 환경변수 설정 확인
- [ ] 데이터베이스 연결 확인
- [ ] 포트 충돌 확인

### 데이터베이스 오류
- [ ] PostgreSQL 서비스 상태 확인
- [ ] DATABASE_URL 형식 확인
- [ ] 데이터베이스 권한 확인

## 📊 모니터링 설정

### Railway 대시보드
- [ ] 실시간 메트릭 확인
- [ ] 로그 스트림 모니터링
- [ ] 리소스 사용량 추적

### 알림 설정
- [ ] 배포 실패 알림
- [ ] 서비스 다운 알림
- [ ] 리소스 사용량 알림

## 🔒 보안 확인

### 환경변수 보안
- [ ] 민감한 정보가 코드에 하드코딩되지 않았는지 확인
- [ ] API 키가 환경변수로 관리되는지 확인
- [ ] .env 파일이 Git에 포함되지 않았는지 확인

### CORS 설정
- [ ] 프로덕션 환경에서 적절한 CORS 설정
- [ ] 허용된 도메인만 접근 가능하도록 설정

## 💰 비용 최적화

### 리소스 조정
- [ ] 필요에 따라 CPU/메모리 조정
- [ ] 사용하지 않는 서비스 중지
- [ ] 자동 스케일링 설정 확인

### 캐싱 전략
- [ ] Redis 캐시 활용 (필요시)
- [ ] 정적 파일 CDN 사용

## 📝 문서화

### 배포 문서
- [ ] README_RAILWAY.md 업데이트
- [ ] 배포 가이드 작성
- [ ] 문제 해결 가이드 작성

### API 문서
- [ ] Swagger UI 접근 가능한지 확인
- [ ] API 엔드포인트 문서화
- [ ] 사용 예제 작성

## 🔄 업데이트 및 롤백

### 새 버전 배포
- [ ] Git 태그 생성
- [ ] 변경사항 문서화
- [ ] 배포 전 테스트 실행

### 롤백 준비
- [ ] 이전 버전 백업
- [ ] 롤백 절차 문서화
- [ ] 데이터베이스 백업

---

## 📞 지원 및 문의

문제가 발생하면 다음 순서로 확인하세요:

1. **Railway 로그 확인**: `railway logs`
2. **애플리케이션 로그 확인**: 애플리케이션 내부 로그
3. **환경변수 설정 확인**: Railway 대시보드
4. **데이터베이스 연결 상태 확인**: PostgreSQL 서비스 상태
5. **네트워크 연결 확인**: 방화벽 및 CORS 설정

## 🎯 성공 기준

배포가 성공적으로 완료되었다고 판단하는 기준:

- [ ] 헬스체크 엔드포인트 응답 (HTTP 200)
- [ ] 모든 API 엔드포인트 정상 작동
- [ ] 데이터베이스 연결 및 쿼리 정상
- [ ] 로그에 오류 없음
- [ ] 응답 시간이 적절함 (< 2초)
- [ ] 메모리 및 CPU 사용량이 정상 범위