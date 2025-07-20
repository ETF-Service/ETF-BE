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

    settings = relationship("InvestmentEtf", back_populates="etf")

class InvestmentEtf(Base):
    __tablename__ = "investment_etfs"
    
    id = Column(Integer, primary_key=True, index=True)
    setting_id = Column(Integer, ForeignKey("investment_settings.id"))
    etf_id = Column(Integer, ForeignKey("etfs.id"))
    created_at = Column(DateTime(timezone=True), server_default=func.now())
    updated_at = Column(DateTime(timezone=True), onupdate=func.now())

    setting = relationship("InvestmentSettings", back_populates="etfs")
    etf = relationship("ETF", back_populates="settings")
