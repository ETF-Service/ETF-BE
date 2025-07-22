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
    etf_symbols: List[str]

    model_config = ConfigDict(
        alias_generator=to_camel,
        populate_by_name=True,
    )

class UserETF(UserETFBase):
    id: int
    etf: ETF
    
    class Config:
        from_attributes = True

# === [추가] ETF별 개별 투자 설정 스키마 ===
class ETFInvestmentSettingBase(BaseModel):
    symbol: Optional[str] = None
    name: Optional[str] = None
    cycle: str  # daily/weekly/monthly
    day: int    # 요일(0~6) 또는 일(1~28)
    amount: float

class ETFInvestmentSettingCreate(ETFInvestmentSettingBase):
    pass

class ETFInvestmentSettingUpdate(BaseModel):
    cycle: Optional[str] = None
    day: Optional[int] = None
    amount: Optional[float] = None

class ETFInvestmentSetting(ETFInvestmentSettingBase):
    id: int
    setting_id: int
    etf_id: int
    created_at: datetime
    updated_at: Optional[datetime] = None
    
    class Config:
        from_attributes = True

class ETFInvestmentSettingsRequest(BaseModel):
    etf_settings: List[ETFInvestmentSettingBase]

class ETFInvestmentSettingsResponse(BaseModel):
    etf_settings: List[ETFInvestmentSetting]

# === 기존 투자 설정 ===
class InvestmentSettingsBase(BaseModel):
    risk_level: int = 5
    api_key: Optional[str] = None
    model_type: str = "clova-x"
    monthly_investment: float = 10.0
    persona: Optional[str] = None

class InvestmentSettingsUpdate(BaseModel):
    risk_level: Optional[int] = None
    api_key: Optional[str] = None
    model_type: Optional[str] = None
    monthly_investment: Optional[float] = None
    persona: Optional[str] = None
    etf_symbols: Optional[List[str]] = None

class InvestmentSettings(InvestmentSettingsBase):
    id: int
    user_id: int
    created_at: datetime
    updated_at: Optional[datetime] = None
    
    class Config:
        from_attributes = True

class InvestmentSettingsResponse(BaseModel):
    settings: Optional[InvestmentSettings] = None 
    etfs: Optional[Sequence[ETF]] = None