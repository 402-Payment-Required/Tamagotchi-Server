import asyncio
import json
import logging
import re

import anthropic

from chat.prompts import SYSTEM_PROMPT
from chat.session import add_turn, get_history

logger = logging.getLogger(__name__)

MODEL = "claude-haiku-4-5"
EMOTIONS = {"happy", "worried", "excited", "sad", "neutral"}
FALLBACK = {
    "reply": "지금은 잘 못 들었어요, 다시 한 번 말씀해 주시겠어요?",
    "emotion": "neutral",
    "signals": {},
}
_JSON_RE = re.compile(r"\{.*\}", re.DOTALL)

# HTTP 요청 자체 타임아웃 (연결/응답 못 받으면 이 시간에 강제 종료 → 토큰 낭비 방지)
_CLIENT_TIMEOUT_S = 25.0
# 재시도 방지: SDK 기본 재시도(2회)를 끄면 실패한 요청이 뒤에서 조용히 돌아가는 일 없음
_CLIENT_MAX_RETRIES = 0
# 코루틴 전체 상한 (SDK timeout이 못 잡는 경우를 대비한 이중 안전장치)
_CALL_TIMEOUT_S = 30.0

# Lazy 초기화: API key가 없어도 import는 성공하도록. 첫 호출 시점에 생성.
_client: anthropic.AsyncAnthropic | None = None


def _get_client() -> anthropic.AsyncAnthropic:
    global _client
    if _client is None:
        _client = anthropic.AsyncAnthropic(
            timeout=_CLIENT_TIMEOUT_S,
            max_retries=_CLIENT_MAX_RETRIES,
        )
    return _client


def _extract_json(raw: str) -> str:
    # LLM이 code fence(```json … ```)로 감싸거나 앞뒤에 부연 텍스트를 붙여도 JSON만 뽑음
    m = _JSON_RE.search(raw)
    return m.group(0) if m else raw


async def chat(message: str, session_id: str) -> dict:
    """
    async: FastAPI가 클라이언트 disconnect 시 이 코루틴을 CancelledError로 취소하고,
    SDK가 취소 신호를 받아 진행 중인 HTTP 요청을 끊음 → 응답 계속 만들다가 토큰 낭비 방지.
    """
    history = get_history(session_id)
    messages = list(history) + [{"role": "user", "content": message}]

    raw = ""
    try:
        response = await asyncio.wait_for(
            _get_client().messages.create(
                model=MODEL,
                max_tokens=200,
                system=[{
                    "type": "text",
                    "text": SYSTEM_PROMPT,
                    "cache_control": {"type": "ephemeral"},
                }],
                messages=messages,
            ),
            timeout=_CALL_TIMEOUT_S,
        )
        raw = next((b.text for b in response.content if b.type == "text"), "")
        data = json.loads(_extract_json(raw))
        if data.get("emotion") not in EMOTIONS:
            data["emotion"] = "neutral"
        data.setdefault("signals", {})
        add_turn(session_id, "user", message)
        add_turn(session_id, "assistant", data["reply"])
        return data
    except asyncio.CancelledError:
        # 클라이언트 disconnect → 상위로 전파해서 진행 중인 HTTP 요청도 취소
        logger.info("engine.chat 취소됨 (client disconnect)")
        raise
    except asyncio.TimeoutError:
        logger.warning("engine.chat 타임아웃 (%.1fs 초과)", _CALL_TIMEOUT_S)
        return dict(FALLBACK)
    except json.JSONDecodeError:
        logger.warning("JSON 파싱 실패 — 원문: %s", raw)
        return dict(FALLBACK)
    except anthropic.APIError:
        logger.exception("Claude API 오류")
        return dict(FALLBACK)
    except Exception:
        logger.exception("engine.chat 오류")
        return dict(FALLBACK)
