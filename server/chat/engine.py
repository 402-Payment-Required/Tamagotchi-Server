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

# Lazy 초기화: API key가 없어도 import는 성공하도록. 첫 호출 시점에 생성.
_client: anthropic.Anthropic | None = None


def _get_client() -> anthropic.Anthropic:
    global _client
    if _client is None:
        _client = anthropic.Anthropic()  # ANTHROPIC_API_KEY 환경변수 자동 사용
    return _client


def _extract_json(raw: str) -> str:
    # LLM이 code fence(```json … ```)로 감싸거나 앞뒤에 부연 텍스트를 붙여도 JSON만 뽑음
    m = _JSON_RE.search(raw)
    return m.group(0) if m else raw


def chat(message: str, session_id: str) -> dict:
    history = get_history(session_id)
    messages = list(history) + [{"role": "user", "content": message}]

    try:
        # cache_control은 프리픽스가 짧으면 no-op이지만 향후 프롬프트 확장 시 자동 캐싱되도록 유지
        response = _get_client().messages.create(
            model=MODEL,
            max_tokens=200,
            system=[{
                "type": "text",
                "text": SYSTEM_PROMPT,
                "cache_control": {"type": "ephemeral"},
            }],
            messages=messages,
        )
        raw = next((b.text for b in response.content if b.type == "text"), "")
        data = json.loads(_extract_json(raw))
        if data.get("emotion") not in EMOTIONS:
            data["emotion"] = "neutral"
        data.setdefault("signals", {})
        add_turn(session_id, "user", message)
        add_turn(session_id, "assistant", data["reply"])
        return data
    except json.JSONDecodeError:
        logger.warning("JSON 파싱 실패 — 원문: %s", raw)
        return dict(FALLBACK)
    except anthropic.APIError:
        logger.exception("Claude API 오류")
        return dict(FALLBACK)
    except Exception:
        logger.exception("engine.chat 오류")
        return dict(FALLBACK)
