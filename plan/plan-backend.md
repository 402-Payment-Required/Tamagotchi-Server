# PLAN — Backend 담당 (B + C 통합) · 서버 기준

> 소유: `server/chat/router.py`, `server/report/`, `server/mission/` 전부
> DB: `users`, `signals`, `mission_progress`
> 책임: A의 `chat()`을 `/chat` API로 노출하고 시그널을 저장한다. 미션(키오스크·타자)의 서버 로직 전체도 담당한다. 서버 뼈대와 공동 파일도 주도한다.

---

## 산출물

1. `main.py` / `db.py` / `schemas.py` — 공동 뼈대 (0시 주도)
2. `chat/router.py` — `POST /chat`
3. `report/router.py` — `GET /report` (부가)
4. `db.py`의 `users`·`signals`·`mission_progress` 헬퍼
5. `mission/router.py` — `/mission/list`, `/start`, `/step`, `/complete`
6. `mission/service.py` — 키오스크 상태머신, 타자 판정
7. `mission/data.py` — 미션 정의 (단계·선택지·정답·힌트)

## 완료 정의 (Definition of Done)

- [ ] FastAPI 서버가 뜨고 CORS로 앱 접근 가능
- [ ] SQLite 3테이블 init 동작
- [ ] `/chat`이 A의 `chat()` 호출 → 결과 반환
- [ ] signals 있으면 저장, user 없으면 자동 생성
- [ ] ngrok로 외부 URL 확보 (앱 연동)
- [ ] `/report` 집계 (부가, 목업 가능)
- [ ] `/mission/list`가 상태 (locked/inprogress/done) 반환
- [ ] `/mission/start`가 첫 단계 반환
- [ ] `/mission/step`이 정답→다음단계 / 오답→힌트 판정
- [ ] `/mission/complete`가 done 처리
- [ ] 키오스크 카페 주문 1개 완주 가능
- [ ] 타자 연습 1개 판정 동작

---

## 타임라인

### 0~1h · 공동 셋업 (Backend 주도)

- 레포에 `server/` FastAPI 뼈대 생성.
- `schemas.py`에 API 계약 전체를 Pydantic 모델로 작성 (문서 4 기준) → A와 확인 후 냉동.
- `db.py`에 3테이블 init + 헬퍼 뼈대.
- `main.py`에 라우터 등록 + CORS (`allow_origins=["*"]` 데모용).
- `main.py`에 mission 라우터 등록될 자리 확보.

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

### 1~2h · Mock /chat + mission/data.py 착수

- A의 `chat()`이 아직이면 Mock으로 리턴하게 두고 프론트와 병행.
- `mission/data.py`에 키오스크 카페 6단계 정의 시작.

```python
# chat/engine.py 임시 Mock (A가 곧 교체)
def chat(message, history=None):
    return {"reply": f"{message}? 우와 할머니!", "emotion": "happy", "signals": {}}
```

### 2~6h · /chat 라우터 + DB 헬퍼 + 미션 서버 구현

**chat 파트**
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

**mission 파트** (독립적으로 자체 완결 개발)
- `mission/service.py` 판정 로직 구현.
- `mission/router.py` 4개 엔드포인트 래핑 + `mission_progress` 갱신.
- curl로 키오스크 1개 완주 검증.

```bash
# curl 검증 예
curl -X POST localhost:8000/mission/start -H 'Content-Type: application/json' \
  -d '{"user_id":"t","mission_id":"kiosk_cafe"}'
curl -X POST localhost:8000/mission/step -H 'Content-Type: application/json' \
  -d '{"user_id":"t","mission_id":"kiosk_cafe","action":"eat_in"}'
```

### 6~9h · A 엔진 연결 + 통합 검증

- A의 실제 `chat()`로 교체된 뒤 전 구간 (앱→/chat→Claude) 확인.
- signals가 실제로 테이블에 쌓이는지 확인.
- 앱(미션 화면)과 연결, 실제 폰에서 키오스크 완주 확인.

### 9~12h · 타자 미션 + report

- 타자·문자 미션 (`typing_1`) 추가: 제시 문장 판정.
- `/report` 구현: signals 집계 요약 (부가). 시간 없으면 목업 데이터 반환.

### 12h~ · 데모 대비

- ngrok URL 안정성 확인 (끊기면 재발급→앱 baseURL 갱신).
- `/chat` 지연·에러 시 앱이 폴백하는지 A와 함께 점검.
- 데모 경로 (키오스크 완주 + 오답→힌트 1회) 리허설.

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

> `mission_progress` CRUD 헬퍼는 `db.py`에 추가하거나 `mission/` 내부에 둔다.

---

## service.py 스케치

```python
from .data import MISSIONS   # {"kiosk_cafe": [steps...], ...}

def start(mission_id):
    steps = MISSIONS[mission_id]
    s = steps[0]
    return {"mission_id": mission_id, "step": 0,
            "prompt": s["prompt"], "options": s["options"], "hint": s["hint"]}

def handle_step(mission_id, current_step, action):
    steps = MISSIONS[mission_id]
    cur = steps[current_step]
    if action in cur["answer"]:
        if cur.get("final"):
            return {"correct": True, "done": True,
                    "message": "주문 완료! 할머니 이제 혼자도 할 수 있어요 🎉"}
        nxt = steps[current_step + 1]
        return {"correct": True, "done": False, "step": nxt["step"],
                "prompt": nxt["prompt"], "options": nxt["options"], "hint": nxt["hint"]}
    return {"correct": False, "done": False, "step": cur["step"],
            "prompt": cur["prompt"], "options": cur["options"], "hint": cur["hint"]}
```

## router.py 스케치 (mission)

```python
from fastapi import APIRouter
from mission import service
from db import get_conn   # mission_progress 갱신용

router = APIRouter(prefix="/mission")

@router.post("/start")
def start(body: dict):
    # mission_progress에 inprogress/current_step=0 upsert
    return service.start(body["mission_id"])

@router.post("/step")
def step(body: dict):
    # 현재 step을 DB에서 읽고 판정, 결과에 따라 current_step/status 갱신
    ...
    return service.handle_step(body["mission_id"], current_step, body["action"])
```

---

## 리스크 & 대비

| 리스크 | 대비 |
|---|---|
| ngrok 세션 끊김 | 재발급 절차 숙지, 앱 baseURL 한 곳(`api.js`)만 고치게 |
| 공동 파일 충돌 | 0시에 완성·냉동, 이후 합의 없이 수정 금지 |
| A 엔진 지연 | Mock으로 프론트 먼저 완성해 병목 회피 |
| 단계 상태 꼬임 (현재 step 추적) | DB의 current_step를 단일 진실로. 프론트가 임의로 안 보냄 |
| 키오스크 UI가 진짜 같지 않음 | 실제 카페 키오스크 스샷 참고, 큰 버튼·명확한 색 |
| 시간 부족 | 키오스크 1개만 완벽히, 타자는 여유 시 |

## 접점

- Backend ← A: `chat()` import.
- Backend → 프론트: `/chat`·`/report`·`/mission/*` JSON (계약 준수).
- Backend ↛ A (미션): 대화 서버 호출 안 함. 힌트는 고정 문구 (A 톤 감수는 선택).
- Backend가 유일하게 쓰는 공유 자원: 3개 테이블 전부 (users·signals·mission_progress).
