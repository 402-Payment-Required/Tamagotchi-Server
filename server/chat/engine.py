import json
import logging

import ollama

from chat.prompts import SYSTEM_PROMPT
from chat.session import add_turn, get_history

logger = logging.getLogger(__name__)

MODEL = "exaone3.5:7.8b"
EMOTIONS = {"happy", "worried", "excited", "sad", "neutral"}
FALLBACK = {
    "reply": "지금은 잘 못 들었어요, 다시 한 번 말씀해 주시겠어요?",
    "emotion": "neutral",
    "signals": {},
}


def chat(message: str, session_id: str) -> dict:
    history = get_history(session_id)
    messages = [{"role": "system", "content": SYSTEM_PROMPT}]
    messages.extend(history)
    messages.append({"role": "user", "content": message})

    try:
        response = ollama.chat(
            model=MODEL,
            messages=messages,
            options={"temperature": 0.7, "num_predict": 200},
        )
        raw = response.message.content
        data = json.loads(raw)
        if data.get("emotion") not in EMOTIONS:
            data["emotion"] = "neutral"
        data.setdefault("signals", {})
        add_turn(session_id, "user", message)
        add_turn(session_id, "assistant", data["reply"])
        return data
    except json.JSONDecodeError:
        logger.warning("JSON 파싱 실패 — 원문: %s", locals().get("raw", "없음"))
        return dict(FALLBACK)
    except Exception:
        logger.exception("Ollama 호출 오류")
        return dict(FALLBACK)
