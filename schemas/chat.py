from pydantic import BaseModel

class ChatMessage(BaseModel):
    content: str

class ChatResponse(BaseModel):
    answer: str 