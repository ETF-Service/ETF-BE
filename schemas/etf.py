from pydantic import BaseModel
from typing import List, Optional, Sequence
from datetime import datetime

class ETFBase(BaseModel):
    symbol: str
    name: str
    description: Optional[str] = None

class ETFCreate(ETFBase):
    pass

class ETF(ETFBase):
    id: int
    created_at: datetime
    updated_at: Optional[datetime] = None
    
    class Config:
        from_attributes = True

class UserPortfolioBase(BaseModel):
    etf_id: int

class UserPortfolioCreate(UserPortfolioBase):
    pass

class UserPortfolio(UserPortfolioBase):
    id: int
    user_id: int
    created_at: datetime
    updated_at: Optional[datetime] = None
    etf: ETF
    
    class Config:
        from_attributes = True

class InvestmentSettingsBase(BaseModel):
    risk_level: int = 5
    api_key: Optional[str] = None
    model_type: str = "gpt-4o"
    monthly_investment: float
    persona: int

class InvestmentSettingsCreate(InvestmentSettingsBase):
    pass

class InvestmentSettingsUpdate(BaseModel):
    risk_level: Optional[int] = None
    api_key: Optional[str] = None
    model_type: Optional[str] = None

class InvestmentSettings(InvestmentSettingsBase):
    id: int
    user_id: int
    created_at: datetime
    updated_at: Optional[datetime] = None
    
    class Config:
        from_attributes = True

class UserPortfolioResponse(BaseModel):
    portfolios: Sequence[UserPortfolio]
    settings: Optional[InvestmentSettings] = None 