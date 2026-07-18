"""
개발용 서버 (AI Mock 모드) — Ollama/모델 없이 즉시 실행

용도:
    - 프론트 개발자가 백엔드 API 구조 확인/테스트할 때
    - CI에서 라우팅·스키마 회귀 확인
    - Ollama·Whisper·MeloTTS 다운로드 없이 API만 돌려볼 때

Mock 동작:
    STT      → 항상 "안녕하세요, 오늘 날씨가 참 좋네요." 반환
    LLM      → 항상 happy·mood:good 응답 (Anthropic API 스텁)
    TTS      → 1초짜리 무음 WAV 반환

실행:
    cd server && uv run python run_dev.py
Swagger:
    http://localhost:8000/docs
"""
import struct
import sys
from unittest.mock import AsyncMock, MagicMock

# ── AI 라이브러리 Mock 주입 (app 임포트 전) ────────────────────────────────────
_whisper_mock = MagicMock()
_whisper_mock.WhisperModel.return_value.transcribe.return_value = (
    [MagicMock(text="안녕하세요, 오늘 날씨가 참 좋네요.")],
    MagicMock(duration=2.0),
)
sys.modules["faster_whisper"] = _whisper_mock

async def _fake_edge_save(path):
    with open(path, "wb") as f:
        f.write(b"\xff\xfb\x90\x00" + b"\x00" * 200)

_edge_communicate_mock = MagicMock()
_edge_communicate_mock.save = AsyncMock(side_effect=_fake_edge_save)

_edge_mock = MagicMock()
_edge_mock.Communicate.return_value = _edge_communicate_mock
sys.modules["edge_tts"] = _edge_mock

_anthropic_mock = MagicMock()
_anthropic_response = MagicMock()
_text_block = MagicMock()
_text_block.type = "text"
_text_block.text = (
    '{"reply": "할머니 오늘 기분은 어떠세요?", "emotion": "happy", "signals": {"mood": "good"}}'
)
_anthropic_response.content = [_text_block]
# AsyncAnthropic()가 반환하는 messages.create는 coroutine이어야 함
_anthropic_mock.AsyncAnthropic.return_value.messages.create = AsyncMock(return_value=_anthropic_response)
_anthropic_mock.Anthropic.return_value.messages.create.return_value = _anthropic_response


class _APIErrorStub(Exception):
    pass


_anthropic_mock.APIError = _APIErrorStub
sys.modules["anthropic"] = _anthropic_mock

# ── 서버 실행 ─────────────────────────────────────────────────────────────────
import uvicorn  # noqa: E402
from main import app  # noqa: E402

if __name__ == "__main__":
    print("=" * 60)
    print("[Mock AI 모드] Ollama·모델·API 키 없이 즉시 실행")
    print("  STT  → 항상 '안녕하세요, 오늘 날씨가 참 좋네요.'")
    print("  LLM  → 항상 happy·mood:good 응답 (Anthropic 스텁)")
    print("  TTS  → 1초짜리 무음 WAV")
    print("-" * 60)
    print(" Swagger UI : http://localhost:8000/docs")
    print(" ReDoc      : http://localhost:8000/redoc")
    print(" LAN 접속   : http://<your-ip>:8000  (0.0.0.0 바인딩)")
    print(" 종료       : Ctrl+C")
    print("=" * 60)
    uvicorn.run(app, host="0.0.0.0", port=8000, reload=False)
