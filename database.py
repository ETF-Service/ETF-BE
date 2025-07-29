from sqlalchemy import create_engine
from sqlalchemy.ext.declarative import declarative_base
from sqlalchemy.orm import sessionmaker
import os

# Railway 환경에서는 PostgreSQL 사용, 로컬에서는 SQLite 사용
DATABASE_URL = os.getenv("DATABASE_URL", "sqlite:///./app.db")

# Railway PostgreSQL URL을 SQLAlchemy 형식으로 변환
if DATABASE_URL.startswith("postgres://"):
    DATABASE_URL = DATABASE_URL.replace("postgres://", "postgresql://", 1)

# SQLite와 PostgreSQL에 따른 엔진 설정
if DATABASE_URL.startswith("sqlite"):
    engine = create_engine(
        DATABASE_URL, 
        connect_args={"check_same_thread": False},
        pool_size=20,
        max_overflow=30,
        pool_pre_ping=True,
    )
else:
    # PostgreSQL 설정
    engine = create_engine(
        DATABASE_URL,
        pool_size=20,
        max_overflow=30,
        pool_pre_ping=True,
    )

SessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)
Base = declarative_base()

# 모델들을 import하여 SQLAlchemy가 테이블을 인식하도록 함
import models

def get_db():
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()
