# CLAUDE.md — 손주 서버 (backend + AI)

> 이 파일은 `server/`에서 작업하는 Claude Code를 위한 가이드다.
> 서버 하나에 **백엔드 로직과 AI(대화 엔진)가 함께** 들어간다.

---

## 프로젝트 한 줄 요약

고령층 디지털 소외 해소 앱 "손주"의 API 서버.
AI 손주와 대화(`/chat`)하고, 대화와 분리된 미션(`/mission/*`)을 수행한다.
해커톤 프로젝트 — 16시간 안에 데모가 도는 게 최우선. 오버엔지니어링 금지.

## 기술 스택

- Python 3.11+
- FastAPI + uvicorn
- Pydantic (요청/응답 검증)
- SQLite (파일 1개, ORM 없음 — sqlite3 직접 사용)
- Anthropic Python SDK (Claude API)

**쓰지 않는 것**: PostgreSQL, Redis, Kafka, Docker, SQLAlchemy/ORM, 인증서버, async DB. 전부 이 규모엔 과함.

## 폴더 구조

```
server/
├── main.py            # FastAPI 앱, 라우터 등록, CORS  ── 공동 소유(냉동)
├── db.py              # SQLite 연결, 테이블 init, 헬퍼 ── 공동 소유(냉동)
├── schemas.py         # Pydantic 모델 = API 계약        ── 공동 소유(냉동)
├── requirements.txt
├── .env               # ANTHROPIC_API_KEY (커밋 금지)
├── .env.example
│
├── chat/              # 대화 기능
│   ├── router.py      # POST /chat            ── B(backend)
│   ├── engine.py      # chat() Claude 호출     ── A(AI)
│   └── prompts.py     # 손주 페르소나 프롬프트  ── A(AI)
│
├── mission/           # 미션 기능             ── C
│   ├── router.py      # /mission/*
│   ├── service.py     # 키오스크 상태머신·판정
│   └── data.py        # 미션 정의(단계·힌트)
│
└── report/            # 보호자 리포트(부가)   ── B
    └── router.py      # GET /report
```

## 소유권 규칙 (충돌 방지 — 반드시 지킬 것)

| 파일/폴더 | 소유자 | 다른 사람 |
|---|---|---|
| `chat/engine.py`, `chat/prompts.py` | A (AI) | 건드리지 말 것 |
| `chat/router.py`, `report/` | B (backend) | — |
| `mission/` 전부 | C | — |
| `main.py`, `db.py`, `schemas.py` | 공동 | 0시에 완성 후 **냉동**. 이후 수정 시 팀 합의 |

- 자기 소유 폴더 밖의 파일을 수정하지 말 것.
- `main.py`/`db.py`/`schemas.py`가 필요하면 수정 대신 팀에 알릴 것.

## API 계약 (핵심 — 절대 형식 변경 금지)

### POST /chat
```
요청:  { "user_id": str, "message": str }
응답:  { "reply": str, "emotion": str, "signals": object }
```
- `emotion` ∈ {happy, worried, excited, sad, neutral} (5종 고정)
- `signals` 예: {"meal": true, "mood": "good"} — 없으면 {}

### GET /mission/list?user_id=
```
응답: { "missions": [ {mission_id, title, type, status}, ... ] }
```
- status ∈ {locked, inprogress, done}, type ∈ {kiosk, typing, sms}

### POST /mission/start
```
요청:  { "user_id": str, "mission_id": str }
응답:  { mission_id, step, prompt, options[], hint }
```

### POST /mission/step
```
요청:  { "user_id": str, "mission_id": str, "action": str }
응답:  { correct, done, step?, prompt?, options?, hint?, message? }
```

### POST /mission/complete
```
요청:  { "user_id": str, "mission_id": str }
응답:  { mission_id, status }
```

> 상세는 `docs/4_API명세서.md` 참조. 이 계약이 프론트와의 유일한 인터페이스다.

## DB 스키마 (SQLite)

```sql
users(user_id PK, character, created_at)
signals(id PK, user_id, type, value, ts)
mission_progress(id PK, user_id, mission_id, status, current_step, completed_at)
```

- `users`, `signals` → B 사용. `mission_progress` → C 사용.
- `db.py`에 세 테이블 init을 모두 넣어둔다.

## Claude API 연동 규칙 (A가 지킴)

- 호출 1번에 reply + emotion + signals를 한 JSON으로 받는다. 쪼개지 말 것.
- 시스템 프롬프트에서 "순수 JSON만 출력"을 강하게 명시.
- `json.loads` 실패 시 폴백: `{reply: 안내문, emotion: "neutral", signals: {}}`. 서버가 500 던지지 않게.
- `max_tokens`는 짧게(≈300). 응답 지연 5초 이내 목표.
- 모델 스트링은 실제 사용 가능한 값인지 확인 후 확정 (예: claude-sonnet-4-6 — 콘솔에서 검증).

## 코딩 규칙

- 예외는 삼키지 말고 로깅하되, `/chat`·`/mission`은 사용자에게 폴백 응답을 준다(앱이 죽지 않게).
- 타입힌트 사용. Pydantic 모델은 `schemas.py`에만 정의하고 import해 쓴다.
- 주석은 "왜"만. 자명한 코드에 주석 달지 말 것.
- 새 라이브러리 추가 시 `requirements.txt`에 반드시 기록.

## 실행

```bash
cd server
pip install -r requirements.txt
cp .env.example .env    # ANTHROPIC_API_KEY 입력
uvicorn main:app --reload --host 0.0.0.0 --port 8000
# 외부 접근(앱 연동): ngrok http 8000
```

## 하지 말 것

- 계약(JSON 형식) 변경. 프론트가 깨진다.
- 소유 폴더 밖 수정.
- ORM/마이그레이션 도입.
- 미션에서 `/chat` 호출 (대화와 미션은 독립).
- `.env` 커밋.