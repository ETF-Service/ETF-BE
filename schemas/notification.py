from pydantic import BaseModel
from typing import Optional
from datetime import datetime

class NotificationBase(BaseModel):
    title: str
    content: str
    type: str  # 'investment_reminder', 'ai_analysis', 'system'

class NotificationCreate(NotificationBase):
    user_id: int

class NotificationUpdate(BaseModel):
    pass

class Notification(NotificationBase):
    id: int
    user_id: int
    created_at: datetime

    class Config:
        from_attributes = True

class NotificationSettings(BaseModel):
    notification_enabled: bool = True

class NotificationSettingsUpdate(BaseModel):
    notification_enabled: Optional[bool] = None