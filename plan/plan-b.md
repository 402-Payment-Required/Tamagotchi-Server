# PLAN — B 담당 (Backend) · 서버 기준

> 소유: `server/chat/router.py`, `server/report/`, DB의 `users`·`signals`
> 책임: A의 `chat()`을 `/chat` API로 노출하고, 시그널을 저장한다. 서버 뼈대와 공동 파일도 주도한다.
> (앱 프론트 대화 화면은 별도 문서 6 참조 — 이 플랜은 서버 파트만 다룬다.)

---

## 산출물

1. `main.py` / `db.py` / `schemas.py` — 공동 뼈대(0시 주도)
2. `chat/router.py` — `POST /chat`
3. `report/router.py` — `GET /report` (부가)
4. `db.py`의 `users`·`signals` 헬퍼

## 완료 정의 (Definition of Done)

- [ ] FastAPI 서버가 뜨고 CORS로 앱 접근 가능
- [ ] SQLite 3테이블 init 동작
- [ ] `/chat`이 A의 `chat()` 호출 → 결과 반환
- [ ] signals 있으면 저장, user 없으면 자동 생성
- [ ] ngrok로 외부 URL 확보(앱 연동)
- [ ] `/report` 집계(부가, 목업 가능)

---

## 타임라인

### 0~1h · 공동 셋업 (B가 주도)
- 레포에 `server/` FastAPI 뼈대 생성.
- `schemas.py`에 API 계약 전체를 Pydantic 모델로 작성(문서 4 기준) → 셋이 확인 후 냉동.
- `db.py`에 3테이블 init + 헬퍼 뼈대.
- `main.py`에 라우터 등록 + CORS(`allow_origins=["*"]` 데모용).

```python
# main.py 핵심
from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from chat.router import router as chat_router
from mission.router import router as mission_router
from report.router import router as report_router
from db import init_db

app = FastAPI()
app.add_middleware(CORSMiddleware, allow_origins=["*"], allow_methods=["*"], allow_headers=["*"])
init_db()
app.include_router(chat_router)
app.include_router(mission_router)
app.include_router(report_router)
```

### 1~2h · Mock /chat
- A의 `chat()`이 아직이면 Mock으로 리턴하게 두고 프론트(문서 6)와 병행.

```python
# chat/engine.py 임시 Mock (A가 곧 교체)
def chat(message, history=None):
    return {"reply": f"{message}? 우와 할머니!", "emotion": "happy", "signals": {}}
```

### 2~6h · /chat 라우터 + DB 헬퍼
- `chat/router.py` 구현: ensure_user → chat() 호출 → save_signals → 반환.
- `db.py`: `ensure_user(user_id)`, `save_signals(user_id, signals)` 구현.

```python
# chat/router.py
from fastapi import APIRouter
from chat.engine import chat
from db import ensure_user, save_signals

router = APIRouter()

@router.post("/chat")
def chat_endpoint(body: dict):
    uid, msg = body["user_id"], body["message"]
    ensure_user(uid)
    result = chat(msg)
    if result.get("signals"):
        save_signals(uid, result["signals"])
    return result
```

### 6~9h · A 엔진 연결 + 검증
- A의 실제 `chat()`로 교체된 뒤 전 구간(앱→/chat→Claude) 확인.
- signals가 실제로 테이블에 쌓이는지 확인.

### 9~12h · 통합 + report
- C의 mission 라우터가 `main.py`에 정상 등록되는지 확인(등록만, 로직은 C).
- `/report` 구현: signals 집계 요약(부가). 시간 없으면 목업 데이터 반환.

### 12h~ · 데모 대비
- ngrok URL 안정성 확인(끊기면 재발급→앱 baseURL 갱신).
- `/chat` 지연·에러 시 앱이 폴백하는지 A와 함께 점검.

---

## DB 헬퍼 스케치 (db.py)

```python
import sqlite3, datetime

def get_conn():
    return sqlite3.connect("sonju.db")

def init_db():
    con = get_conn(); c = con.cursor()
    c.execute("CREATE TABLE IF NOT EXISTS users(user_id TEXT PRIMARY KEY, character TEXT DEFAULT 'grandson', created_at TEXT)")
    c.execute("CREATE TABLE IF NOT EXISTS signals(id INTEGER PRIMARY KEY AUTOINCREMENT, user_id TEXT, type TEXT, value TEXT, ts TEXT)")
    c.execute("CREATE TABLE IF NOT EXISTS mission_progress(id INTEGER PRIMARY KEY AUTOINCREMENT, user_id TEXT, mission_id TEXT, status TEXT, current_step INTEGER DEFAULT 0, completed_at TEXT)")
    con.commit(); con.close()

def ensure_user(uid):
    con = get_conn(); c = con.cursor()
    c.execute("INSERT OR IGNORE INTO users(user_id, created_at) VALUES(?,?)", (uid, datetime.datetime.now().isoformat()))
    con.commit(); con.close()

def save_signals(uid, signals: dict):
    con = get_conn(); c = con.cursor(); now = datetime.datetime.now().isoformat()
    for k, v in signals.items():
        c.execute("INSERT INTO signals(user_id, type, value, ts) VALUES(?,?,?,?)", (uid, k, str(v), now))
    con.commit(); con.close()
```

> `mission_progress`는 C가 사용. B는 테이블 init만 제공하고 로직은 안 건드림.

---

## 리스크 & 대비

| 리스크 | 대비 |
|---|---|
| ngrok 세션 끊김 | 재발급 절차 숙지, 앱 baseURL 한 곳(`api.js`)만 고치게 |
| 공동 파일 충돌 | 0시에 완성·냉동, 이후 합의 없이 수정 금지 |
| A 엔진 지연 | Mock으로 프론트 먼저 완성해 병목 회피 |

## 접점

- B ← A: `chat()` import.
- B ↔ C: `main.py`에 mission 라우터 등록 자리 제공(등록만).
- B → 프론트: `/chat`·`/report` JSON (계약 준수).
- 