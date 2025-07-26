from sqlalchemy import create_engine
from sqlalchemy.ext.declarative import declarative_base
from sqlalchemy.orm import sessionmaker

DATABASE_URL = "sqlite:///./app.db"

engine = create_engine(
    DATABASE_URL, 
	connect_args={"check_same_thread": False},
	pool_size=20,
	max_overflow=30,
	poll_pre_ping=True,
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
