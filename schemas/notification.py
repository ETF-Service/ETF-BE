from pydantic import BaseModel
from typing import Optional
from datetime import datetime

class NotificationBase(BaseModel):
    title: str
    content: str
    type: str  # 'investment_reminder', 'ai_analysis', 'system'
    sent_via: Optional[str] = None  # 'app', 'email', 'sms'

class NotificationCreate(NotificationBase):
    user_id: int

class NotificationUpdate(BaseModel):
    is_read: Optional[bool] = None
    read_at: Optional[datetime] = None

class Notification(NotificationBase):
    id: int
    user_id: int
    is_read: bool
    created_at: datetime
    read_at: Optional[datetime] = None

    class Config:
        from_attributes = True

class NotificationSettings(BaseModel):
    notification_enabled: bool = True
    notification_channels: str = 'app'  # 'app,email,sms'

class NotificationSettingsUpdate(BaseModel):
    notification_enabled: Optional[bool] = None
    notification_channels: Optional[str] = None 