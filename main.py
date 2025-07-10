from fastapi import FastAPI
from pydantic import BaseModel

app = FastAPI()

class User(BaseModel):
    name: str
    risk_level: int
    etfs: list[str]

@app.get("/")
def root():
    return {"message": "ETF FastAPI 백엔드가 실행 중입니다."}

@app.get("/ping")
def ping():
    return {"ping": "pong"}

@app.post("/user")
def save_user(user: User):
    return {"status": "ok", "user": user}
