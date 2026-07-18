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

def _fake_tts_to_file(text, speaker_id, path, quiet=False):
    num_samples = 16000  # 1초 분량 silence
    data_size = num_samples * 2
    with open(path, "wb") as f:
        f.write(b"RIFF")
        f.write(struct.pack("<I", 36 + data_size))
        f.write(b"WAVEfmt ")
        f.write(struct.pack("<IHHIIHH", 16, 1, 1, 16000, 32000, 2, 16))
        f.write(b"data")
        f.write(struct.pack("<I", data_size))
        f.write(b"\x00" * data_size)

_melo_api_mock = MagicMock()
_tts_instance = MagicMock()
_tts_instance.hps.data.spk2id = {"KR": 0}
_tts_instance.tts_to_file.side_effect = _fake_tts_to_file
_melo_api_mock.TTS.return_value = _tts_instance
sys.modules["melo"] = MagicMock()
sys.modules["melo.api"] = _melo_api_mock

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
    print("=" * 50)
    print("[Mock AI 모드] 서버 시작")
    print("Swagger UI : http://localhost:8000/docs")
    print("ReDoc      : http://localhost:8000/redoc")
    print("종료       : Ctrl+C")
    print("=" * 50)
    uvicorn.run(app, host="0.0.0.0", port=8000, reload=False)
