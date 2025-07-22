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

    settings = relationship("InvestmentETFSettings", back_populates="etf")

class InvestmentETFSettings(Base):
    __tablename__ = "investment_etfs"
    
    id = Column(Integer, primary_key=True, index=True)
    setting_id = Column(Integer, ForeignKey("investment_settings.id"))
    etf_id = Column(Integer, ForeignKey("etfs.id"))
    # 개별 ETF 투자 설정
    cycle = Column(String, nullable=False)   # 투자 주기: daily/weekly/monthly
    day = Column(Integer, nullable=False)    # 투자 일: 요일(0~6) 또는 일(1~28)
    amount = Column(Float, nullable=False)   # 투자 금액(만원)
    created_at = Column(DateTime(timezone=True), server_default=func.now())
    updated_at = Column(DateTime(timezone=True), onupdate=func.now())

    setting = relationship("InvestmentSettings", back_populates="etfs")
    etf = relationship("ETF", back_populates="settings")
