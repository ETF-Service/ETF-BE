# ETF Backend Railway 배포 가이드

## 개요
이 문서는 ETF Backend 프로젝트를 Railway에서 배포하는 방법을 설명합니다.

## 사전 준비사항

### 1. Railway 계정 및 CLI 설치
- [Railway](https://railway.app) 계정 생성
- Railway CLI 설치:
  ```bash
  npm install -g @railway/cli
  ```

### 2. 프로젝트 준비
- Git 저장소에 코드 푸시
- 필요한 환경변수 준비

## 배포 단계

### 1. Railway CLI 로그인
```bash
railway login
```

### 2. 프로젝트 초기화
```bash
cd ETF_BE
railway init
```

### 3. PostgreSQL 데이터베이스 추가
```bash
railway add
```
- PostgreSQL 선택
- 데이터베이스 생성

### 4. 환경변수 설정
Railway 대시보드에서 다음 환경변수들을 설정:

#### 필수 환경변수
- `DATABASE_URL`: Railway PostgreSQL URL (자동 설정됨)
- `PORT`: 포트 번호 (자동 설정됨)

#### 선택적 환경변수
- `SECRET_KEY`: JWT 토큰 암호화 키
- `ALGORITHM`: JWT 알고리즘 (기본값: HS256)
- `ACCESS_TOKEN_EXPIRE_MINUTES`: 토큰 만료 시간 (기본값: 30)
- `OPENAI_API_KEY`: OpenAI API 키 (AI 기능 사용 시)

### 5. 배포 실행
```bash
railway up
```

### 6. 도메인 설정 (선택사항)
```bash
railway domain
```

## 배포 확인

### 1. 헬스체크
```bash
curl https://your-app-name.railway.app/health
```

### 2. 로그 확인
```bash
railway logs
```

### 3. 실시간 로그 모니터링
```bash
railway logs --follow
```

## 주요 특징

### 1. 자동 데이터베이스 마이그레이션
- 애플리케이션 시작 시 자동으로 테이블 생성
- ETF 초기 데이터 자동 로드

### 2. 헬스체크 엔드포인트
- `/`: 기본 헬스체크
- `/health`: 상세 헬스체크

### 3. 로깅 시스템
- Railway 환경에서는 콘솔 로그만 사용
- 로그 레벨: INFO

### 4. 스케줄러 서비스
- 알림 스케줄러 자동 시작/중지
- 서버 생명주기와 연동

## 문제 해결

### 1. 빌드 실패
```bash
# 로컬에서 빌드 테스트
docker build -t etf-backend .
docker run -p 8000:8000 etf-backend
```

### 2. 데이터베이스 연결 오류
- `DATABASE_URL` 환경변수 확인
- PostgreSQL 서비스 상태 확인

### 3. 포트 충돌
- Railway는 자동으로 `PORT` 환경변수 설정
- 애플리케이션에서 `$PORT` 사용

### 4. 메모리 부족
- Railway 대시보드에서 리소스 할당 증가
- 불필요한 의존성 제거

## 모니터링

### 1. Railway 대시보드
- 실시간 메트릭 확인
- 로그 스트림 모니터링
- 리소스 사용량 추적

### 2. 알림 설정
- 배포 실패 알림
- 서비스 다운 알림
- 리소스 사용량 알림

## 비용 최적화

### 1. 리소스 조정
- 필요에 따라 CPU/메모리 조정
- 사용하지 않는 서비스 중지

### 2. 캐싱 전략
- Redis 캐시 활용 (필요시)
- 정적 파일 CDN 사용

## 보안 고려사항

### 1. 환경변수 관리
- 민감한 정보는 Railway 환경변수로 관리
- `.env` 파일은 Git에 포함하지 않음

### 2. CORS 설정
- 프로덕션 환경에서 적절한 CORS 설정
- 허용된 도메인만 접근 가능하도록 설정

### 3. API 키 관리
- OpenAI API 키 등 민감한 키는 환경변수로 관리
- 키 순환 정책 수립

## 업데이트 및 롤백

### 1. 새 버전 배포
```bash
git push origin main
railway up
```

### 2. 롤백
- Railway 대시보드에서 이전 버전으로 롤백
- Git 태그를 사용한 버전 관리

## 지원 및 문의

문제가 발생하면 다음을 확인하세요:
1. Railway 로그 확인
2. 애플리케이션 로그 확인
3. 환경변수 설정 확인
4. 데이터베이스 연결 상태 확인 