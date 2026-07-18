# AGENTS.md — 손주 서버 (backend + AI)

> 코딩 에이전트(Codex, Cursor, 기타)를 위한 표준 가이드. `server/` 디렉터리 기준.
> 내용은 `CLAUDE.md`와 동일한 규칙을 따른다.

---

## Overview

고령층 디지털 소외 해소 앱 "손주"의 API 서버. 백엔드 로직과 AI 음성 파이프라인이 한 서버에 공존한다.
해커톤(16시간) 프로젝트 — 데모 동작이 최우선. 최소 구현 원칙.

- 음성 대화: `POST /voice/*` (STT → LLM → TTS, 세션 기반 멀티턴)
- 미션: `POST /mission/*` (키오스크·타자 연습, 대화와 분리)

## Tech stack

- Python 3.11+, FastAPI, uvicorn, Pydantic
- SQLite (sqlite3 직접, ORM 없음)
- faster-whisper (STT, 로컬)
- Ollama exaone3.5:7.8b (LLM, 로컬, localhost:11434)
- MeloTTS-Korean (TTS, 로컬)

Do NOT introduce: Anthropic/OpenAI cloud APIs, PostgreSQL, Redis, Kafka, Docker, ORM, auth server, async DB.

## Directory layout

```
server/
├── main.py              # app entry, routers, CORS        [shared, frozen]
├── db.py                # SQLite init + helpers            [shared, frozen]
├── schemas.py           # Pydantic models = contract       [shared, frozen]
├── chat/
│   ├── voice_router.py  # POST /voice/*                    [owner: B]
│   ├── router.py        # POST /chat (optional)            [owner: B]
│   ├── session.py       # session & history management     [owner: A]
│   ├── stt.py           # faster-whisper wrapper           [owner: A]
│   ├── tts.py           # MeloTTS-Korean wrapper           [owner: A]
│   ├── engine.py        # Ollama multi-turn call           [owner: A]
│   └── prompts.py       # grandson persona prompt          [owner: A]
├── mission/             # all mission logic                [owner: B]
│   ├── router.py
│   ├── service.py
│   └── data.py
└── report/              # GET /report (optional)           [owner: B]
```

## Ownership rules (avoid conflicts)

- Only edit files within your assigned area.
- `main.py`, `db.py`, `schemas.py` are shared and frozen after hour 0. Do not modify without team agreement.
- `chat/engine.py`, `chat/prompts.py`, `chat/stt.py`, `chat/tts.py`, `chat/session.py` belong to A (AI). Do not touch when working on backend tasks.

## API contract (do NOT change shapes)

```
POST /voice/start
  req  { user_id: str }
  res  { session_id: str }

POST /voice/chat
  req  multipart/form-data { user_id: str, session_id: str, audio: File }
  res  { audio: str(base64), reply: str, emotion: str, signals: object }
       emotion ∈ {happy, worried, excited, sad, neutral}

POST /voice/end
  req  { user_id: str, session_id: str }
  res  { status: "ended" }

GET  /mission/list?user_id=
  res  { missions: [ {mission_id, title, type, status} ] }
       status ∈ {locked, inprogress, done}

POST /mission/start
  req  { user_id, mission_id }
  res  { mission_id, step, prompt, options[], hint }

POST /mission/step
  req  { user_id, mission_id, action }
  res  { correct, done, step?, prompt?, options?, hint?, message? }

POST /mission/complete
  req  { user_id, mission_id }
  res  { mission_id, status }
```

## Database (SQLite)

```
users(user_id PK, character, created_at)
signals(id PK, user_id, type, value, ts)
mission_progress(id PK, user_id, mission_id, status, current_step, completed_at)
```

## Voice pipeline rules (chat/engine.py, stt.py, tts.py)

- Pipeline order: audio → STT → text → Ollama → {reply, emotion, signals} → TTS → audio bytes.
- Load STT/TTS models once at server startup. Never reload per request.
- One Ollama call returns reply + emotion + signals as a single JSON object. Never split calls.
- System prompt must force pure-JSON output with 3 examples.
- On `json.loads` failure, fall back to `{reply, emotion:"neutral", signals:{}}`. Never raise 500 to the client.
- Session history is in-memory. Reset on server restart is acceptable.
- Ollama base URL: `localhost:11434`.

## Conversation flow

```
[start button] → POST /voice/start → session_id
[recording]   → (silence timeout or stop button)
              → POST /voice/chat (audio file)
              → STT → Ollama(history) → TTS → response
[stop button] → POST /voice/end
```

## Conventions

- Use type hints. Define Pydantic models only in `schemas.py`.
- `/voice` and `/mission` endpoints must degrade gracefully (fallback response, never crash the app).
- Record any new dependency in `requirements.txt`.
- Comments explain "why", not "what".

## Setup / run

```bash
# Start Ollama first
ollama serve
ollama pull exaone3.5:7.8b

# Run server
cd server
pip install -r requirements.txt
uvicorn main:app --reload --host 0.0.0.0 --port 8000
```

## Never do

- Change the JSON contract shapes.
- Edit files outside your ownership area.
- Add an ORM or migrations.
- Call `/voice` from mission logic (voice chat and mission are independent).
- Commit `.env`.
- Use cloud LLM APIs (Anthropic, OpenAI, etc.).
