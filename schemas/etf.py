from pydantic import BaseModel
from typing import List, Optional, Sequence
from datetime import datetime
from pydantic import ConfigDict
from pydantic.alias_generators import to_camel

class ETFBase(BaseModel):
    symbol: str
    name: str
    description: Optional[str] = None

class ETFCreate(ETFBase):
    pass

class ETF(ETFBase):
    id: int
    
    class Config:
        from_attributes = True

class UserETFResponse(BaseModel):
	etfs: Sequence[ETF]

class UserETFBase(BaseModel):
    etf_id: int
    setting_id: int

class UserETFUpdate(BaseModel):
    etf_id: int

    model_config = ConfigDict(
        alias_generator=to_camel,
        populate_by_name=True,
    )

class UserETF(UserETFBase):
    id: int
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
    monthly_investment: Optional[float] = None

class InvestmentSettings(InvestmentSettingsBase):
    id: int
    user_id: int
    created_at: datetime
    updated_at: Optional[datetime] = None
    
    class Config:
        from_attributes = True

class InvestmentSettingsResponse(BaseModel):
    settings: Optional[InvestmentSettings] = None 