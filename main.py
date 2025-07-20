from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from contextlib import asynccontextmanager
from routers import user as user_router
from routers import etf as etf_router
from routers import chat as chat_router
from database import engine, Base
from crud.etf import create_initial_etfs, get_all_etfs

@asynccontextmanager
async def lifespan(app: FastAPI):
    # 서버 시작 시 실행
    try:
        # 데이터베이스 테이블 생성
        Base.metadata.create_all(bind=engine)
        print("✅ 데이터베이스 테이블 생성 완료")
        
        # ETF 데이터 초기화
        from sqlalchemy.orm import Session
        db = Session(engine)
        try:
            create_initial_etfs(db)
            print("✅ ETF 데이터 초기화 완료")
        except Exception as e:
            print(f"⚠️ ETF 데이터가 이미 존재하거나 초기화 실패: {e}")
        finally:
            db.close()
            
    except Exception as e:
        print(f"❌ 서버 초기화 중 오류 발생: {e}")
    
    yield
    
    # 서버 종료 시 실행 (필요시)

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