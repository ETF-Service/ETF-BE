from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from routers import user as user_router
from routers import etf as etf_router
from routers import chat as chat_router

app = FastAPI()

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

app.include_router(user_router.router)
app.include_router(etf_router.router)
app.include_router(chat_router.router) 