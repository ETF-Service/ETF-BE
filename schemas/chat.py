from pydantic import BaseModel
from datetime import datetime
from typing import List, Optional

class ChatMessageBase(BaseModel):
    content: str

class ChatMessageCreate(ChatMessageBase):
    pass

class ChatMessage(ChatMessageBase):
    id: int
    user_id: int
    role: str
    content: str
    created_at: datetime
    
    class Config:
        from_attributes = True

class ChatHistory(BaseModel):
    messages: List[ChatMessage]
    total_count: int 

class ChatResponse(BaseModel):
    content: str