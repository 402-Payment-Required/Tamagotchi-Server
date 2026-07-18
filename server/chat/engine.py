import json
import os

from anthropic import Anthropic
from dotenv import load_dotenv

from .prompts import SYSTEM_PROMPT

load_dotenv()

client = Anthropic(api_key=os.environ.get("ANTHROPIC_API_KEY"))
MODEL = "claude-sonnet-4-5"  # 콘솔에서 실제 사용 가능한 모델명인지 확인 후 확정할 것

EMOTIONS = {"happy", "worried", "excited", "sad", "neutral"}

FALLBACK = {
    "reply": "지금은 대답하기 어려워요, 다시 한 번 말씀해 주시겠어요?",
    "emotion": "neutral",
    "signals": {},
}


def chat(message: str, history=None) -> dict:
    try:
        resp = client.messages.create(
            model=MODEL,
            max_tokens=300,
            system=SYSTEM_PROMPT,
            messages=[{"role": "user", "content": message}],
        )
        data = json.loads(resp.content[0].text)
        if data.get("emotion") not in EMOTIONS:
            data["emotion"] = "neutral"
        data.setdefault("signals", {})
        return data
    except Exception:
        return dict(FALLBACK)
