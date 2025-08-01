FROM python:3.11-slim

# 작업 디렉토리 설정
WORKDIR /app

# 시스템 의존성 설치 (최소화)
RUN apt-get update && apt-get install -y \
    gcc \
    g++ \
    curl \
    && apt-get clean \
    && rm -rf /var/lib/apt/lists/*

# Python 의존성 복사 및 설치
COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

# 애플리케이션 코드 복사
COPY . .

# Railway는 PORT 환경변수를 자동으로 설정
EXPOSE 8000

# Railway용 실행 명령 - shell 형식으로 환경변수 확장
CMD uvicorn main:app --host 0.0.0.0 --port 8000