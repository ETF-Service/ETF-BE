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

class UserETFBase(BaseModel):
    setting_id: int
    etf_id: int

class UserETFUpdate(UserETFBase):
    pass

class UserETF(UserETFBase):
    id: int
    created_at: datetime
    updated_at: Optional[datetime] = None
    etf: ETF
    
    class Config:
        from_attributes = True

class InvestmentSettingsBase(BaseModel):
    risk_level: int = 5
    api_key: Optional[str] = None
    model_type: str = "clova-x"
    monthly_investment: float = 10.0
    persona: Optional[str] = None

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
    settings: Optional[InvestmentSettings] = None 
    etfs: Sequence[UserETFBase] = []