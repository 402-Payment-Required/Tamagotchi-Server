from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from chat.router import router as chat_router
from db import init_db
from mission.router import router as mission_router
from report.router import router as report_router

app = FastAPI()
app.add_middleware(
    CORSMiddleware, allow_origins=["*"], allow_methods=["*"], allow_headers=["*"]
)

init_db()

app.include_router(chat_router)
app.include_router(mission_router)
app.include_router(report_router)
