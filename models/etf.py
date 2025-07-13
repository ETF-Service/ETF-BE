from sqlalchemy import Column, Integer, String, Float, ForeignKey, DateTime
from sqlalchemy.orm import relationship
from sqlalchemy.sql import func
from database import Base

class ETF(Base):
    __tablename__ = "etfs"
    
    id = Column(Integer, primary_key=True, index=True)
    symbol = Column(String, unique=True, index=True)  # SPY, QQQ 등
    name = Column(String)  # 미국 S&P500, 미국 나스닥 등
    description = Column(String, nullable=True)
    created_at = Column(DateTime(timezone=True), server_default=func.now())
    updated_at = Column(DateTime(timezone=True), onupdate=func.now())

class UserPortfolio(Base):
    __tablename__ = "user_portfolios"
    
    id = Column(Integer, primary_key=True, index=True)
    user_id = Column(Integer, ForeignKey("users.id"))
    etf_id = Column(Integer, ForeignKey("etfs.id"))
    monthly_investment = Column(Float, default=0.0)  # 월 투자 금액
    created_at = Column(DateTime(timezone=True), server_default=func.now())
    updated_at = Column(DateTime(timezone=True), onupdate=func.now())
    
    # 관계 설정
    user = relationship("User", back_populates="portfolios")
    etf = relationship("ETF")

class InvestmentSettings(Base):
    __tablename__ = "investment_settings"
    
    id = Column(Integer, primary_key=True, index=True)
    user_id = Column(Integer, ForeignKey("users.id"), unique=True)
    risk_level = Column(Integer, default=5)  # 0-10 투자 성향
    api_key = Column(String, nullable=True)  # AI 서비스 API 키
    model_type = Column(String, default="gpt-4o")  # 사용할 AI 모델
    created_at = Column(DateTime(timezone=True), server_default=func.now())
    updated_at = Column(DateTime(timezone=True), onupdate=func.now())
    
    # 관계 설정
    user = relationship("User", back_populates="settings") 