from pydantic import BaseModel, Field

class UserCreate(BaseModel):
    user_id: str = Field(..., min_length=3, max_length=30)
    password: str = Field(..., min_length=6, max_length=100)
    name: str = Field(..., min_length=1, max_length=100)
    email: str = Field(..., min_length=5, max_length=100)

class UserLogin(BaseModel):
    user_id: str = Field(..., min_length=3, max_length=30)
    password: str = Field(..., min_length=6, max_length=100)
