import asyncio
import base64
import inspect
import json
import logging
import struct
import uuid

from fastapi import APIRouter, File, Form, UploadFile
from fastapi.responses import StreamingResponse

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
    from chat.tts import synthesize, stream_synthesize
    from chat.session import start_session, end_session
except ImportError:
    logger.warning("A 모듈(stt/tts/session) 없음 — Mock 사용")

    def transcribe(audio_bytes: bytes) -> str:
        return "안녕하세요"

    def synthesize(text: str) -> bytes:
        return b""

    async def stream_synthesize(text: str):
        yield b""

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
        _r = engine_chat(text, session_id)
        result = await _r if inspect.isawaitable(_r) else _r
        if result.get("signals"):
            save_signals(user_id, result["signals"])
        _s = synthesize(result["reply"])
        tts_bytes = await _s if inspect.isawaitable(_s) else _s
        return VoiceChatResponse(
            audio=base64.b64encode(tts_bytes).decode(),
            reply=result["reply"],
            emotion=result.get("emotion", "neutral"),
            signals=result.get("signals", {}),
        )
    except Exception:
        logger.exception("voice_chat 오류")
        return FALLBACK_RESPONSE


@router.post("/stream")
async def voice_stream(
    user_id: str = Form(...),
    session_id: str = Form(...),
    audio: UploadFile = File(...),
):
    """
    NDJSON 스트리밍 엔드포인트.
    첫 줄: {"type":"meta","reply":"...","emotion":"...","signals":{}}
    이후:  {"type":"audio","data":"<base64 MP3 chunk>"}  (청크마다)
    마지막: {"type":"done"}
    """
    async def generate():
        meta_sent = False
        try:
            audio_bytes = await audio.read()
            text = transcribe(audio_bytes)

            _r = engine_chat(text, session_id)
            result = await _r if inspect.isawaitable(_r) else _r

            if result.get("signals"):
                save_signals(user_id, result["signals"])

            yield json.dumps({
                "type": "meta",
                "reply": result["reply"],
                "emotion": result.get("emotion", "neutral"),
                "signals": result.get("signals", {}),
            }, ensure_ascii=False) + "\n"
            meta_sent = True

            try:
                async for chunk in stream_synthesize(result["reply"]):
                    yield json.dumps({
                        "type": "audio",
                        "data": base64.b64encode(chunk).decode(),
                    }) + "\n"
            except Exception:
                # TTS 오류 — meta는 이미 전송됐으므로 오디오만 생략하고 done으로 마무리
                logger.warning("voice_stream TTS 오류 — 오디오 생략")

            yield json.dumps({"type": "done"}) + "\n"

        except asyncio.CancelledError:
            raise
        except Exception:
            logger.exception("voice_stream 오류")
            if not meta_sent:
                yield json.dumps({
                    "type": "meta",
                    "reply": "지금은 대답하기 어려워요, 다시 한 번 말씀해 주시겠어요?",
                    "emotion": "neutral",
                    "signals": {},
                }, ensure_ascii=False) + "\n"
            yield json.dumps({"type": "done"}) + "\n"

    return StreamingResponse(generate(), media_type="application/x-ndjson")


@router.post("/end", response_model=VoiceEndResponse)
def voice_end(body: VoiceEndRequest):
    try:
        end_session(body.session_id)
    except Exception:
        logger.exception("voice_end 오류")
    return VoiceEndResponse(status="ended")
