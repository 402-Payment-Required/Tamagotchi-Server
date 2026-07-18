# AGENTS.md — 손주 서버 (backend + AI)

> 코딩 에이전트(Codex, Cursor, 기타)를 위한 표준 가이드. `server/` 디렉터리 기준.
> 내용은 `CLAUDE.md`와 동일한 규칙을 따른다.

---

## Overview

고령층 디지털 소외 해소 앱 "손주"의 API 서버. 백엔드 로직과 AI 대화 엔진이 한 서버에 공존한다.
해커톤(16시간) 프로젝트 — 데모 동작이 최우선. 최소 구현 원칙.

- 대화: `POST /chat` (AI 손주 응답 + 감정 + 시그널)
- 미션: `POST /mission/*` (키오스크·타자 연습, 대화와 분리)

## Tech stack

- Python 3.11+, FastAPI, uvicorn, Pydantic
- SQLite (sqlite3 직접, ORM 없음)
- Anthropic Python SDK

Do NOT introduce: PostgreSQL, Redis, Kafka, Docker, ORM, auth server, async DB.

## Directory layout

```
server/
├── main.py         # app entry, routers, CORS   [shared, frozen]
├── db.py           # SQLite init + helpers        [shared, frozen]
├── schemas.py      # Pydantic models = contract   [shared, frozen]
├── chat/
│   ├── router.py   # POST /chat                   [owner: B]
│   ├── engine.py   # chat() -> Claude             [owner: A]
│   └── prompts.py  # grandson persona             [owner: A]
├── mission/        # all mission logic            [owner: C]
│   ├── router.py
│   ├── service.py
│   └── data.py
└── report/         # GET /report (optional)       [owner: B]
```

## Ownership rules (avoid conflicts)

- Only edit files within your assigned area.
- `main.py`, `db.py`, `schemas.py` are shared and frozen after hour 0. Do not modify without team agreement.
- `chat/engine.py` + `chat/prompts.py` belong to A (AI). Do not touch when working on backend tasks.

## API contract (do NOT change shapes)

```
POST /chat
  req  { user_id: str, message: str }
  res  { reply: str, emotion: str, signals: object }
       emotion ∈ {happy, worried, excited, sad, neutral}

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

Full spec: `docs/4_API명세서.md`.

## Database (SQLite)

```
users(user_id PK, character, created_at)
signals(id PK, user_id, type, value, ts)
mission_progress(id PK, user_id, mission_id, status, current_step, completed_at)
```

## Claude API rules (chat/engine.py)

- One API call returns reply + emotion + signals as a single JSON object. Never split calls.
- System prompt must force pure-JSON output.
- On `json.loads` failure, fall back to `{reply, emotion:"neutral", signals:{}}`. Never raise 500 to the client.
- Keep `max_tokens` small (~300). Target <5s latency.
- Verify the model string against the console before committing (e.g. claude-sonnet-4-6).

## Conventions

- Use type hints. Define Pydantic models only in `schemas.py`.
- `/chat` and `/mission` endpoints must degrade gracefully (fallback response, never crash the app).
- Record any new dependency in `requirements.txt`.
- Comments explain "why", not "what".

## Setup / run

```bash
cd server
pip install -r requirements.txt
cp .env.example .env      # set ANTHROPIC_API_KEY
uvicorn main:app --reload --host 0.0.0.0 --port 8000
ngrok http 8000           # expose for the Expo app
```

## Never do

- Change the JSON contract shapes.
- Edit files outside your ownership area.
- Add an ORM or migrations.
- Call `/chat` from mission logic (chat and mission are independent).
- Commit `.env`.