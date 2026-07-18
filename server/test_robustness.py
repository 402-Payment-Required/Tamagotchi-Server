"""
서버 견고성 검증 — API key 실수·client disconnect·타임아웃·인증 실패에서도
앱이 죽지 않고 fallback으로 안전하게 응답하는지 확인.
실행: cd server && uv run python test_robustness.py

주의: 검증 4는 실제 Anthropic 서버로 401 요청을 보냄 (요금 부과 없음).
     오프라인 환경에서 검증 4는 network 에러로 대체됨 (역시 fallback 처리).
"""
import asyncio
import io
import os
import sys
from unittest.mock import AsyncMock, MagicMock, patch

# ── psycopg2/DB mock — PostgreSQL 없이도 서버 임포트 가능하게 ──────────────────
_fake_cursor = MagicMock()
_fake_cursor.__enter__ = lambda s: s
_fake_cursor.__exit__ = lambda s, *a: None
_fake_cursor.fetchone.return_value = None
_fake_cursor.fetchall.return_value = []
_fake_conn = MagicMock()
_fake_conn.cursor.return_value = _fake_cursor
_fake_conn.__enter__ = lambda s: s
_fake_conn.__exit__ = lambda s, *a: None
_psycopg2_mock = MagicMock()
_psycopg2_mock.connect.return_value = _fake_conn
_psycopg2_extras_mock = MagicMock()
_psycopg2_extras_mock.RealDictCursor = MagicMock()
sys.modules["psycopg2"] = _psycopg2_mock
sys.modules["psycopg2.extras"] = _psycopg2_extras_mock

# ── faster_whisper mock ────────────────────────────────────────────────────────
_whisper_mock = MagicMock()
_whisper_mock.WhisperModel.return_value.transcribe.return_value = (
    [MagicMock(text="테스트 발화입니다")], MagicMock(duration=1.0),
)
sys.modules["faster_whisper"] = _whisper_mock

# ── edge_tts mock ──────────────────────────────────────────────────────────────
async def _fake_edge_save(path):
    with open(path, "wb") as f:
        f.write(b"\xff\xfb\x90\x00" + b"\x00" * 200)

_edge_communicate_mock = MagicMock()
_edge_communicate_mock.save = AsyncMock(side_effect=_fake_edge_save)
_edge_mock = MagicMock()
_edge_mock.Communicate.return_value = _edge_communicate_mock
sys.modules["edge_tts"] = _edge_mock


if sys.platform == "win32":
    sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding="utf-8", errors="replace")


_pass = 0
_fail = 0


def check(label: str, cond: bool, detail: str = "") -> None:
    global _pass, _fail
    if cond:
        _pass += 1
        print(f"  [PASS] {label}")
    else:
        _fail += 1
        print(f"  [FAIL] {label}" + (f" — {detail}" if detail else ""))


async def test_import_without_key() -> None:
    print("\n[1] API key 없이 서버 임포트")
    saved = os.environ.pop("ANTHROPIC_API_KEY", None)
    try:
        from main import app  # noqa: F401
        check("app 정상 로드 (라우트 8개)", len(app.routes) >= 8)
    finally:
        if saved is not None:
            os.environ["ANTHROPIC_API_KEY"] = saved


async def test_cancellation_propagates() -> None:
    print("\n[2] 클라이언트 disconnect 시나리오 (CancelledError 재-raise)")
    os.environ.setdefault("ANTHROPIC_API_KEY", "sk-ant-test-stub")
    from chat import engine
    from chat.session import start_session

    sid = start_session("cancel_test")

    async def never(*_a, **_kw):
        await asyncio.sleep(999)

    with patch.object(engine, "_get_client") as gc:
        gc.return_value.messages.create = never
        task = asyncio.create_task(engine.chat("안녕", sid))
        await asyncio.sleep(0.1)
        task.cancel()
        try:
            await task
            check("CancelledError 정상 전파", False, "취소 안 됨")
        except asyncio.CancelledError:
            check("CancelledError 정상 전파 (Claude 요청 중단됨)", True)


async def test_timeout_fallback() -> None:
    print("\n[3] Claude API 응답 지연 → 타임아웃 → fallback")
    from chat import engine
    from chat.session import start_session

    sid = start_session("timeout_test")

    async def slow(*_a, **_kw):
        await asyncio.sleep(999)

    with patch.object(engine, "_CALL_TIMEOUT_S", 0.2), \
         patch.object(engine, "_get_client") as gc:
        gc.return_value.messages.create = slow
        result = await engine.chat("안녕", sid)
        check("타임아웃 시 fallback 반환", result["reply"] == engine.FALLBACK["reply"])


async def test_invalid_key_fallback() -> None:
    print("\n[4] 잘못된 API key → 인증 실패/네트워크 실패 → fallback")
    os.environ["ANTHROPIC_API_KEY"] = "sk-ant-invalid-key-for-robustness-test"
    # 캐시된 클라이언트 초기화
    from chat import engine
    engine._client = None
    from chat.session import start_session

    sid = start_session("auth_test")
    result = await engine.chat("안녕", sid)
    check("인증/네트워크 실패 시 fallback 반환", result["reply"] == engine.FALLBACK["reply"])


async def test_sdk_hardening_config() -> None:
    print("\n[5] SDK 안전장치 (재시도 차단, 타임아웃 25s)")
    from chat import engine
    engine._client = None  # 재생성
    client = engine._get_client()
    check("max_retries=0 (실패 요청 재시도 없음)", client.max_retries == 0)
    check(f"timeout={engine._CLIENT_TIMEOUT_S}s (HTTP 요청 상한)", client.timeout == engine._CLIENT_TIMEOUT_S)


async def test_tts_network_failure_fallback() -> None:
    print("\n[6] edge-tts 네트워크 오류 → fallback 응답 (앱 죽지 않음)")
    import struct, base64, uuid
    from fastapi.testclient import TestClient
    from main import app

    client = TestClient(app)

    # edge_tts.Communicate.save를 예외로 패치
    async def _fail_save(path):
        raise ConnectionError("network unreachable")

    _edge_mock.Communicate.return_value.save = AsyncMock(side_effect=_fail_save)
    try:
        num = 1600
        ds = num * 2
        wav = (
            b"RIFF" + struct.pack("<I", 36 + ds) + b"WAVEfmt "
            + struct.pack("<IHHIIHH", 16, 1, 1, 16000, 32000, 2, 16)
            + b"data" + struct.pack("<I", ds) + b"\x00" * ds
        )
        r = client.post(
            "/voice/chat",
            data={"user_id": "rob_test", "session_id": str(uuid.uuid4())},
            files={"audio": ("test.wav", wav, "audio/wav")},
        )
        check("TTS 오류 시 200 응답 (앱 죽지 않음)", r.status_code == 200)
        check("TTS 오류 시 fallback reply 반환", bool(r.json().get("reply")))
    finally:
        # 정상 mock 복구
        _edge_mock.Communicate.return_value.save = AsyncMock(side_effect=_fake_edge_save)


async def main() -> None:
    print("=" * 60)
    print("견고성 검증 — 어떤 상황에도 앱이 죽지 않는지")
    print("=" * 60)
    await test_import_without_key()
    await test_cancellation_propagates()
    await test_timeout_fallback()
    await test_invalid_key_fallback()
    await test_sdk_hardening_config()
    await test_tts_network_failure_fallback()

    total = _pass + _fail
    print(f"\n{'=' * 60}")
    print(f"결과: {_pass}/{total} 통과" + ("" if _fail == 0 else f"  ({_fail}개 실패)"))
    print("=" * 60)
    sys.exit(0 if _fail == 0 else 1)


if __name__ == "__main__":
    asyncio.run(main())
