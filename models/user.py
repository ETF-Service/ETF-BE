from sqlalchemy import Column, Integer, String, DateTime, ForeignKey, Float, Boolean, Text
from sqlalchemy.orm import relationship
from sqlalchemy.sql import func
from database import Base

class User(Base):
    __tablename__ = "users"

    id = Column(Integer, primary_key=True, index=True)
    user_id = Column(String, unique=True, index=True, nullable=False)
    hashed_password = Column(String, nullable=False)
    name = Column(String, nullable=False)
    email = Column(String, unique=True, index=True, nullable=False)
    created_at = Column(DateTime(timezone=True), server_default=func.now())
    updated_at = Column(DateTime(timezone=True), onupdate=func.now())

    settings = relationship("InvestmentSettings", back_populates="user", uselist=False)
    chat_messages = relationship("ChatMessage", back_populates="user")
    notifications = relationship("Notification", back_populates="user")

class InvestmentSettings(Base):
    __tablename__ = "investment_settings"

    id = Column(Integer, primary_key=True, index=True)
    user_id = Column(Integer, ForeignKey("users.id"), unique=True)
    risk_level = Column(Integer, default=5)
    api_key = Column(String, nullable=False)
    model_type = Column(String, nullable=False)
    persona = Column(String, nullable=True)
    notification_enabled = Column(Boolean, default=True)
    last_analysis_result = Column(Text, nullable=True, default=None) # 새로 추가된 컬럼
    last_analysis_at = Column(DateTime(timezone=True), nullable=True, default=None) # 마지막 분석 시간
    created_at = Column(DateTime(timezone=True), server_default=func.now())
    updated_at = Column(DateTime(timezone=True), onupdate=func.now())

    user = relationship("User", back_populates="settings", uselist=False)
    etfs = relationship("InvestmentETFSettings", back_populates="setting")
