from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from contextlib import asynccontextmanager
import logging
from logging.handlers import RotatingFileHandler
import os
from datetime import datetime, timezone, timedelta
from dotenv import load_dotenv
from config.timezone_config import get_kst_now

# .env 파일 로드
load_dotenv()

from routers import user as user_router
from routers import etf as etf_router
from routers import chat as chat_router
from database import engine, Base
from crud.etf import create_initial_etfs, get_all_etfs

# 모델들을 명시적으로 import하여 순환 참조 문제 해결
import models

# 로그 디렉토리 생성
def setup_logging():
    """로깅 설정 초기화"""
    # logs 디렉토리 생성 (권한 오류 시 무시)
    log_dir = "logs"
    try:
        if not os.path.exists(log_dir):
            os.makedirs(log_dir)
        log_file = f"{log_dir}/app_{get_kst_now().strftime('%Y-%m-%d')}.log"
        file_handler = RotatingFileHandler(log_file, maxBytes=10*1024*1024, backupCount=5, encoding='utf-8')
    except (OSError, PermissionError):
        # Railway 환경에서는 파일 로그 대신 콘솔 로그만 사용
        file_handler = None
    
    # 핸들러 설정
    handlers = [logging.StreamHandler()]  # 콘솔 핸들러는 항상 포함
    if file_handler:
        handlers.append(file_handler)
    
    # 로깅 설정
    logging.basicConfig(
        level=logging.INFO,  # Railway에서는 INFO 레벨 사용
        format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
        handlers=handlers
    )
    
    # 로거 생성
    logger = logging.getLogger(__name__)
    logger.info("로깅 시스템 초기화 완료")
    if file_handler:
        logger.info(f"로그 파일 위치: {log_file}")
    else:
        logger.info("파일 로그 비활성화 (콘솔 로그만 사용)")
    
    return logger

@asynccontextmanager
async def lifespan(app: FastAPI):
    # 로깅 설정
    logger = setup_logging()
    
    # 서버 시작 시 실행
    try:
        logger.info("서버 시작 중...")
        
        # 데이터베이스 테이블 생성
        Base.metadata.create_all(bind=engine)
        logger.info("✅ 데이터베이스 테이블 생성 완료")
        
        # ETF 데이터 초기화
        from sqlalchemy.orm import Session
        db = Session(engine)
        try:
            create_initial_etfs(db)
            db.commit()
            logger.info("✅ ETF 데이터 초기화 완료")
        except Exception as e:
            logger.warning(f"⚠️ ETF 데이터가 이미 존재하거나 초기화 실패: {e}")
        finally:
            db.close()
        
        # 알림 스케줄러 시작
        try:
            from services.scheduler_service import start_notification_scheduler
            start_notification_scheduler()
            logger.info("✅ 알림 스케줄러 시작 완료")
        except Exception as e:
            logger.warning(f"⚠️ 알림 스케줄러 시작 실패: {e}")
            
    except Exception as e:
        logger.error(f"❌ 서버 초기화 중 오류 발생: {e}")
        raise
    
    logger.info("서버 시작 완료")
    yield
    
    # 서버 종료 시 실행
    logger.info("서버 종료 중...")
    
    # 알림 스케줄러 중지
    try:
        from services.scheduler_service import stop_notification_scheduler
        stop_notification_scheduler()
        logger.info("✅ 알림 스케줄러 중지 완료")
    except Exception as e:
        logger.warning(f"⚠️ 알림 스케줄러 중지 실패: {e}")

app = FastAPI(lifespan=lifespan)

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# 헬스체크 엔드포인트 추가
@app.get("/")
async def health_check():
    """Railway 헬스체크용 엔드포인트"""
    return {"status": "healthy", "message": "ETF Backend API is running"}

@app.get("/health")
async def health():
    """추가 헬스체크 엔드포인트"""
    return {"status": "ok"}

app.include_router(user_router.router)
app.include_router(etf_router.router)
app.include_router(chat_router.router)

# Railway 배포용 - uvicorn 실행 설정
if __name__ == "__main__":
    import uvicorn
    port = int(os.environ.get("PORT", 8000))
    uvicorn.run(app, host="0.0.0.0", port=port)