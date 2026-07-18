from fastapi import APIRouter

from chat.engine import chat
from db import ensure_user, save_signals
from schemas import ChatRequest, ChatResponse

router = APIRouter()


@router.post("/chat", response_model=ChatResponse)
def chat_endpoint(body: ChatRequest):
    ensure_user(body.user_id)
    result = chat(body.message)
    if result.get("signals"):
        save_signals(body.user_id, result["signals"])
    return result
