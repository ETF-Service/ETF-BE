from sqlalchemy import Column, Integer, String, DateTime, ForeignKey
from sqlalchemy.orm import relationship
from sqlalchemy.sql import func
from database import Base
from pydantic import ConfigDict
from pydantic.alias_generators import to_camel

class User(Base):
    __tablename__ = "users"

    id = Column(Integer, primary_key=True, index=True)
    user_id = Column(String, unique=True, index=True, nullable=False)  # 로그인용 고유 아이디
    hashed_password = Column(String, nullable=False)
    name = Column(String, nullable=False)  # 실명/닉네임
    email = Column(String, unique=True, index=True, nullable=False)
    created_at = Column(DateTime(timezone=True), server_default=func.now())
    updated_at = Column(DateTime(timezone=True), onupdate=func.now())

    portfolios = relationship("UserPortfolio", back_populates="user")
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
    monthly_investment = Column(Integer)
    persona = Column(Integer, ForeignKey("chat_messages.id"))
    created_at = Column(DateTime(timezone=True), server_default=func.now())
    updated_at = Column(DateTime(timezone=True), onupdate=func.now())

    user = relationship("User", back_populates="settings")
