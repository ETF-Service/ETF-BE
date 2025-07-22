from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from contextlib import asynccontextmanager
import logging
import os
from datetime import datetime
from routers import user as user_router
from routers import etf as etf_router
from routers import chat as chat_router
from database import engine, Base
from crud.etf import create_initial_etfs, get_all_etfs

# 로그 디렉토리 생성
def setup_logging():
    """로깅 설정 초기화"""
    # logs 디렉토리 생성
    log_dir = "logs"
    if not os.path.exists(log_dir):
        os.makedirs(log_dir)
    
    # 로그 파일명 (날짜별)
    today = datetime.now().strftime("%Y-%m-%d")
    log_file = f"{log_dir}/app_{today}.log"
    
    # 로깅 설정
    logging.basicConfig(
        level=logging.INFO,
        format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
        handlers=[
            # 파일 핸들러 (로그 파일에 저장)
            logging.FileHandler(log_file, encoding='utf-8'),
            # 콘솔 핸들러 (터미널에도 출력)
            logging.StreamHandler()
        ]
    )
    
    # 로거 생성
    logger = logging.getLogger(__name__)
    logger.info("로깅 시스템 초기화 완료")
    logger.info(f"로그 파일 위치: {os.path.abspath(log_file)}")
    
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
            
    except Exception as e:
        logger.error(f"❌ 서버 초기화 중 오류 발생: {e}")
        raise
    
    logger.info("서버 시작 완료")
    yield
    
    # 서버 종료 시 실행
    logger.info("서버 종료 중...")

app = FastAPI(lifespan=lifespan)

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

app.include_router(user_router.router)
app.include_router(etf_router.router)
app.include_router(chat_router.router) 