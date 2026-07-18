"""
HTTP API 엔드포인트 테스트 (Ollama/모델/DB 없이 실행 가능)
실행: cd server && uv run python test_api.py
"""

import base64
import io
import struct
import sys
from unittest.mock import AsyncMock, MagicMock

# Windows 콘솔 UTF-8 출력
if sys.platform == "win32":
    sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding="utf-8", errors="replace")
    sys.stderr = io.TextIOWrapper(sys.stderr.buffer, encoding="utf-8", errors="replace")

# ── AI 라이브러리를 모듈 임포트 전에 패치 ──────────────────────────────────────
_whisper_mock = MagicMock()
_whisper_mock.WhisperModel.return_value.transcribe.return_value = (
    [MagicMock(text="테스트 발화입니다")],
    MagicMock(duration=1.0),
)
sys.modules["faster_whisper"] = _whisper_mock

_melo_api_mock = MagicMock()
_tts_instance = MagicMock()
_tts_instance.hps.data.spk2id = {"KR": 0}


def _fake_tts_to_file(text, speaker_id, path, quiet=False):
    num_samples = 1600
    data_size = num_samples * 2
    with open(path, "wb") as f:
        f.write(b"RIFF")
        f.write(struct.pack("<I", 36 + data_size))
        f.write(b"WAVEfmt ")
        f.write(struct.pack("<IHHIIHH", 16, 1, 1, 16000, 32000, 2, 16))
        f.write(b"data")
        f.write(struct.pack("<I", data_size))
        f.write(b"\x00" * data_size)


_tts_instance.tts_to_file.side_effect = _fake_tts_to_file
_melo_api_mock.TTS.return_value = _tts_instance
sys.modules["melo"] = MagicMock()
sys.modules["melo.api"] = _melo_api_mock

# ── AI 백엔드 mock: 실제 API 절대 호출 금지 ────────────────────────────────────
# Ollama mock (현재 main의 engine.py)
_FAKE_REPLY = '{"reply": "네 안녕하세요.", "emotion": "happy", "signals": {"mood": "good"}}'
_ollama_mock = MagicMock()
_ollama_response = MagicMock()
_ollama_response.message.content = _FAKE_REPLY
_ollama_mock.chat.return_value = _ollama_response
sys.modules["ollama"] = _ollama_mock

# Anthropic mock (A팀 feat/ai-claude-api 머지 후 engine.py)
_anthropic_mock = MagicMock()
_anthropic_response = MagicMock()
_text_block = MagicMock()
_text_block.type = "text"
_text_block.text = _FAKE_REPLY
_anthropic_response.content = [_text_block]
_anthropic_mock.AsyncAnthropic.return_value.messages.create = AsyncMock(return_value=_anthropic_response)
_anthropic_mock.Anthropic.return_value.messages.create.return_value = _anthropic_response


class _APIErrorStub(Exception):
    pass


_anthropic_mock.APIError = _APIErrorStub
sys.modules["anthropic"] = _anthropic_mock

# psycopg2 mock — CI/로컬에 PostgreSQL 서버가 없어도 서버 임포트가 성공하도록
_psycopg2_mock = MagicMock()
_fake_cursor = MagicMock()
_fake_cursor.__enter__ = lambda s: s
_fake_cursor.__exit__ = lambda s, *a: None
_fake_cursor.fetchone.return_value = None
_fake_cursor.fetchall.return_value = []
_fake_conn = MagicMock()
_fake_conn.cursor.return_value = _fake_cursor
_fake_conn.__enter__ = lambda s: s
_fake_conn.__exit__ = lambda s, *a: None
_psycopg2_mock.connect.return_value = _fake_conn
_psycopg2_extras_mock = MagicMock()
_psycopg2_extras_mock.RealDictCursor = MagicMock()
sys.modules["psycopg2"] = _psycopg2_mock
sys.modules["psycopg2.extras"] = _psycopg2_extras_mock

# ── 이제 app 임포트 ────────────────────────────────────────────────────────────
from fastapi.testclient import TestClient  # noqa: E402
from main import app  # noqa: E402

client = TestClient(app)

# ── 유틸 ───────────────────────────────────────────────────────────────────────
_pass = 0
_fail = 0


def check(label: str, cond: bool, detail: str = ""):
    global _pass, _fail
    if cond:
        _pass += 1
        print(f"  [PASS] {label}")
    else:
        _fail += 1
        print(f"  [FAIL] {label}" + (f" — {detail}" if detail else ""))


def _minimal_wav() -> bytes:
    num_samples = 1600
    data_size = num_samples * 2
    buf = io.BytesIO()
    buf.write(b"RIFF")
    buf.write(struct.pack("<I", 36 + data_size))
    buf.write(b"WAVEfmt ")
    buf.write(struct.pack("<IHHIIHH", 16, 1, 1, 16000, 32000, 2, 16))
    buf.write(b"data")
    buf.write(struct.pack("<I", data_size))
    buf.write(b"\x00" * data_size)
    return buf.getvalue()


# ── 테스트 ─────────────────────────────────────────────────────────────────────

def test_mission():
    print("\n[미션 엔드포인트]")
    USER = "test_user_api"
    MID = "kiosk_cafe"

    r = client.get(f"/mission/list?user_id={USER}")
    check("GET /mission/list — 200", r.status_code == 200)
    missions = r.json().get("missions", [])
    check("GET /mission/list — missions 배열", isinstance(missions, list) and len(missions) > 0)
    ids = [m["mission_id"] for m in missions]
    check("GET /mission/list — kiosk_cafe 포함", "kiosk_cafe" in ids)

    r = client.post("/mission/start", json={"user_id": USER, "mission_id": MID})
    check("POST /mission/start — 200", r.status_code == 200)
    body = r.json()
    check("POST /mission/start — step/prompt/options/hint", all(k in body for k in ("step", "prompt", "options", "hint")))

    r = client.post("/mission/step", json={"user_id": USER, "mission_id": MID, "action": "매장에서 먹기"})
    check("POST /mission/step 정답 — correct=True", r.json().get("correct") is True)
    check("POST /mission/step 정답 — done=False", r.json().get("done") is False)

    r = client.post("/mission/step", json={"user_id": USER, "mission_id": MID, "action": "엉뚱한 답"})
    check("POST /mission/step 오답 — correct=False", r.json().get("correct") is False)

    r = client.post("/mission/complete", json={"user_id": USER, "mission_id": MID})
    check("POST /mission/complete — status=done", r.json().get("status") == "done")


def test_voice():
    print("\n[음성 엔드포인트]")
    USER = "test_user_api"

    r = client.post("/voice/start", json={"user_id": USER})
    check("POST /voice/start — 200", r.status_code == 200)
    session_id = r.json().get("session_id", "")
    check("POST /voice/start — session_id 존재", bool(session_id))

    wav = _minimal_wav()
    r = client.post(
        "/voice/chat",
        data={"user_id": USER, "session_id": session_id},
        files={"audio": ("test.wav", wav, "audio/wav")},
    )
    check("POST /voice/chat — 200", r.status_code == 200)
    body = r.json()
    check("POST /voice/chat — audio(base64)", bool(body.get("audio")))
    check("POST /voice/chat — reply", bool(body.get("reply")))
    check("POST /voice/chat — emotion 유효값", body.get("emotion") in {"happy", "worried", "excited", "sad", "neutral"})
    if body.get("audio"):
        try:
            base64.b64decode(body["audio"])
            check("POST /voice/chat — audio base64 디코딩 가능", True)
        except Exception:
            check("POST /voice/chat — audio base64 디코딩 가능", False, "base64 디코딩 실패")

    r = client.post("/voice/end", json={"user_id": USER, "session_id": session_id})
    check("POST /voice/end — status=ended", r.json().get("status") == "ended")


def test_report():
    print("\n[리포트 엔드포인트]")
    USER = "test_user_api"

    r = client.get(f"/report?user_id={USER}")
    check("GET /report — 200", r.status_code == 200)
    check("GET /report — signals 배열", isinstance(r.json().get("signals"), list))


# ── 실행 ───────────────────────────────────────────────────────────────────────
if __name__ == "__main__":
    print("=" * 50)
    print("API 엔드포인트 테스트 (Mock AI + Mock DB 모드)")
    print("=" * 50)

    try:
        test_mission()
        test_voice()
        test_report()
    except Exception as e:
        print(f"\n예외 발생: {e}")
        import traceback
        traceback.print_exc()
        sys.exit(1)

    total = _pass + _fail
    print(f"\n{'=' * 50}")
    print(f"결과: {_pass}/{total} 통과" + ("" if _fail == 0 else f"  ({_fail}개 실패)"))
    print("=" * 50)
    sys.exit(0 if _fail == 0 else 1)
