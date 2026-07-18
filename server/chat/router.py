import logging

from fastapi import APIRouter

from chat.engine import chat
from chat.session import end_session, start_session
from db import ensure_user, save_signals
from schemas import ChatRequest, ChatResponse

logger = logging.getLogger(__name__)
router = APIRouter()

FALLBACK = {"reply": "지금은 대답하기 어려워요, 다시 한 번 말씀해 주시겠어요?", "emotion": "neutral", "signals": {}}


@router.post("/chat", response_model=ChatResponse)
async def chat_endpoint(body: ChatRequest):
    # async: client disconnect 시 engine.chat 코루틴이 취소되어 Claude API 요청도 중단됨
    session_id = None
    try:
        ensure_user(body.user_id)
        # 텍스트 챗은 요청당 세션 (음성 흐름의 /voice/start와 분리)
        session_id = start_session(body.user_id)
        result = await chat(body.message, session_id)
        if result.get("signals"):
            save_signals(body.user_id, result["signals"])
        return result
    except Exception:
        logger.exception("chat_endpoint 오류")
        return FALLBACK
    finally:
        if session_id:
            end_session(session_id)
