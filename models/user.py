from sqlalchemy import Column, Integer, String, DateTime, ForeignKey, Float
from sqlalchemy.orm import relationship
from sqlalchemy.sql import func
from database import Base
from pydantic import ConfigDict
from pydantic.alias_generators import to_camel

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

    model_config = ConfigDict(
        alias_generator=to_camel,
        populate_by_name=True,
    )

class InvestmentSettings(Base):
    __tablename__ = "investment_settings"
    id = Column(Integer, primary_key=True, index=True)
    user_id = Column(Integer, ForeignKey("users.id"), unique=True)
    risk_level = Column(Integer, default=5)
    api_key = Column(String, nullable=False)
    model_type = Column(String, nullable=False)
    monthly_investment = Column(Float, default=10.0) # 만원 단위
    persona = Column(Integer, ForeignKey("chat_messages.id"), nullable=True)  # 특정 채팅 메시지 참조
    created_at = Column(DateTime(timezone=True), server_default=func.now())
    updated_at = Column(DateTime(timezone=True), onupdate=func.now())

    etfs = relationship("InvestmentEtf", back_populates="setting")
    user = relationship("User", back_populates="settings", uselist=False)
    persona_message = relationship("ChatMessage", back_populates="persona_settings", uselist=False)
