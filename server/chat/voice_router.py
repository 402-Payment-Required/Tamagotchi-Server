import base64
import logging
import struct
import uuid

from fastapi import APIRouter, File, Form, UploadFile

from db import ensure_user, save_signals
from schemas import VoiceChatResponse, VoiceEndRequest, VoiceEndResponse, VoiceStartRequest, VoiceStartResponse

logger = logging.getLogger(__name__)


def _silent_wav_b64() -> str:
    # 프론트가 재생 실패하지 않도록 최소 유효 WAV (0.1초 무음, 16kHz mono 16bit)
    num = 1600
    ds = num * 2
    buf = (
        b"RIFF" + struct.pack("<I", 36 + ds) + b"WAVEfmt "
        + struct.pack("<IHHIIHH", 16, 1, 1, 16000, 32000, 2, 16)
        + b"data" + struct.pack("<I", ds) + b"\x00" * ds
    )
    return base64.b64encode(buf).decode()


_SILENT_WAV_B64 = _silent_wav_b64()

try:
    from chat.stt import transcribe
    from chat.tts import synthesize
    from chat.session import start_session, end_session
except ImportError:
    logger.warning("A 모듈(stt/tts/session) 없음 — Mock 사용")

    def transcribe(audio_bytes: bytes) -> str:
        return "안녕하세요"

    def synthesize(text: str) -> bytes:
        return b""

    def start_session(user_id: str) -> str:
        return str(uuid.uuid4())

    def end_session(session_id: str) -> None:
        pass

try:
    from chat.engine import chat as engine_chat
except ImportError:
    def engine_chat(message: str, session_id: str) -> dict:
        return {"reply": "잠시 후 다시 말씀해 주세요.", "emotion": "neutral", "signals": {}}

router = APIRouter(prefix="/voice")

FALLBACK_RESPONSE = VoiceChatResponse(
    audio=_SILENT_WAV_B64,
    reply="지금은 대답하기 어려워요, 다시 한 번 말씀해 주시겠어요?",
    emotion="neutral",
    signals={},
)


@router.post("/start", response_model=VoiceStartResponse)
def voice_start(body: VoiceStartRequest):
    try:
        ensure_user(body.user_id)
        session_id = start_session(body.user_id)
    except Exception:
        logger.exception("voice_start 오류")
        session_id = str(uuid.uuid4())
    return VoiceStartResponse(session_id=session_id)


@router.post("/chat", response_model=VoiceChatResponse)
async def voice_chat(
    user_id: str = Form(...),
    session_id: str = Form(...),
    audio: UploadFile = File(...),
):
    try:
        audio_bytes = await audio.read()
        text = transcribe(audio_bytes)
        result = engine_chat(text, session_id)
        if result.get("signals"):
            save_signals(user_id, result["signals"])
        tts_bytes = synthesize(result["reply"])
        return VoiceChatResponse(
            audio=base64.b64encode(tts_bytes).decode(),
            reply=result["reply"],
            emotion=result.get("emotion", "neutral"),
            signals=result.get("signals", {}),
        )
    except Exception:
        logger.exception("voice_chat 오류")
        return FALLBACK_RESPONSE


@router.post("/end", response_model=VoiceEndResponse)
def voice_end(body: VoiceEndRequest):
    try:
        end_session(body.session_id)
    except Exception:
        logger.exception("voice_end 오류")
    return VoiceEndResponse(status="ended")
