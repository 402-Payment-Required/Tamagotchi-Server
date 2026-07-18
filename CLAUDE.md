# CLAUDE.md — 손주 서버 (backend + AI)

> 이 파일은 `server/`에서 작업하는 Claude Code를 위한 가이드다.
> 서버 하나에 **백엔드 로직과 AI(음성 파이프라인)가 함께** 들어간다.

---

## 프로젝트 한 줄 요약

고령층 디지털 소외 해소 앱 "손주"의 API 서버.
AI 손주와 **음성**으로 대화(`/voice/*`)하고, 대화와 분리된 미션(`/mission/*`)을 수행한다.
해커톤 프로젝트 — 16시간 안에 데모가 도는 게 최우선. 오버엔지니어링 금지.

## 기술 스택

- Python 3.11+
- FastAPI + uvicorn
- Pydantic (요청/응답 검증)
- SQLite (파일 1개, ORM 없음 — sqlite3 직접 사용)
- faster-whisper (STT, 로컬)
- Ollama exaone3.5:7.8b (LLM, 로컬)
- MeloTTS-Korean (TTS, 로컬)

**쓰지 않는 것**: Anthropic/OpenAI 등 클라우드 LLM API, PostgreSQL, Redis, Kafka, Docker, SQLAlchemy/ORM, 인증서버, async DB. 전부 이 규모엔 과함.

## 폴더 구조

```
server/
├── main.py                # FastAPI 앱, 라우터 등록, CORS  ── 공동 소유(냉동)
├── db.py                  # SQLite 연결, 테이블 init, 헬퍼 ── 공동 소유(냉동)
├── schemas.py             # Pydantic 모델 = API 계약        ── 공동 소유(냉동)
├── requirements.txt
├── .env                   # 환경변수 (커밋 금지)
├── .env.example
│
├── chat/                  # 음성 대화 기능
│   ├── voice_router.py    # POST /voice/*         ── B(backend)
│   ├── router.py          # POST /chat (선택 유지) ── B(backend)
│   ├── session.py         # 세션/히스토리 관리     ── A(AI)
│   ├── stt.py             # faster-whisper 래퍼    ── A(AI)
│   ├── tts.py             # MeloTTS-Korean 래퍼    ── A(AI)
│   ├── engine.py          # Ollama 멀티턴 호출     ── A(AI)
│   └── prompts.py         # 손주 페르소나 프롬프트  ── A(AI)
│
├── mission/               # 미션 기능             ── B
│   ├── router.py          # /mission/*
│   ├── service.py         # 키오스크 상태머신·판정
│   └── data.py            # 미션 정의(단계·힌트)
│
└── report/                # 보호자 리포트(부가)   ── B
    └── router.py          # GET /report
```

## 소유권 규칙 (충돌 방지 — 반드시 지킬 것)

| 파일/폴더 | 소유자 | 다른 사람 |
|---|---|---|
| `chat/engine.py`, `chat/prompts.py`, `chat/stt.py`, `chat/tts.py`, `chat/session.py` | A (AI) | 건드리지 말 것 |
| `chat/voice_router.py`, `chat/router.py`, `report/` | B (backend) | — |
| `mission/` 전부 | B | — |
| `main.py`, `db.py`, `schemas.py` | 공동 | 0시에 완성 후 **냉동**. 이후 수정 시 팀 합의 |

- 자기 소유 폴더 밖의 파일을 수정하지 말 것.
- `main.py`/`db.py`/`schemas.py`가 필요하면 수정 대신 팀에 알릴 것.

## API 계약 (핵심 — 절대 형식 변경 금지)

### POST /voice/start
```
요청:  { "user_id": str }
응답:  { "session_id": str }
```

### POST /voice/chat
```
요청:  multipart/form-data { user_id: str, session_id: str, audio: File }
응답:  { "audio": str(base64), "reply": str, "emotion": str, "signals": object }
```
- `emotion` ∈ {happy, worried, excited, sad, neutral} (5종 고정)
- `signals` 예: {"meal": true, "mood": "good"} — 없으면 {}

### POST /voice/end
```
요청:  { "user_id": str, "session_id": str }
응답:  { "status": "ended" }
```

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

## DB 스키마 (SQLite)

```sql
users(user_id PK, character, created_at)
signals(id PK, user_id, type, value, ts)
mission_progress(id PK, user_id, mission_id, status, current_step, completed_at)
```

## 음성 파이프라인 규칙 (A가 지킴)

- STT → LLM → TTS 순서. 단계별 함수로 분리, 각각 단독 테스트 가능하게.
- Ollama 호출 1번에 reply + emotion + signals를 한 JSON으로 받는다. 쪼개지 말 것.
- 시스템 프롬프트에서 "순수 JSON만 출력"을 강하게 명시, 예시 3개 포함.
- `json.loads` 실패 시 폴백: `{reply: 안내문, emotion: "neutral", signals: {}}`. 서버가 500 던지지 않게.
- STT/TTS 모델은 서버 시작 시 1회만 로드. 요청마다 재로드 금지.
- Ollama는 `localhost:11434` 기준. 서버 미실행 시 명확한 에러 메시지.
- 세션 히스토리는 in-memory (서버 재시작 시 초기화 허용).

## 대화 흐름

```
[시작 버튼] → POST /voice/start → session_id 발급
[녹음] → (무음 타임아웃 or 종료 버튼)
→ POST /voice/chat (audio 전송)
→ STT → 텍스트 → Ollama(히스토리) → {reply, emotion, signals} → TTS → 오디오
→ 응답 반환 → 프론트 오디오 재생 → 다시 녹음 대기
[종료 버튼] → POST /voice/end
```

## 코딩 규칙

- 예외는 삼키지 말고 로깅하되, `/voice`·`/mission`은 사용자에게 폴백 응답을 준다(앱이 죽지 않게).
- 타입힌트 사용. Pydantic 모델은 `schemas.py`에만 정의하고 import해 쓴다.
- 주석은 "왜"만. 자명한 코드에 주석 달지 말 것.
- 새 라이브러리 추가 시 `requirements.txt`에 반드시 기록.

## 실행

```bash
# Ollama 먼저 실행
ollama serve
ollama pull exaone3.5:7.8b

# 서버 실행
cd server
pip install -r requirements.txt
uvicorn main:app --reload --host 0.0.0.0 --port 8000
```

## 하지 말 것

- 계약(JSON 형식) 변경. 프론트가 깨진다.
- 소유 폴더 밖 수정.
- ORM/마이그레이션 도입.
- 미션에서 `/voice` 호출 (대화와 미션은 독립).
- `.env` 커밋.
- 클라우드 LLM API(Anthropic, OpenAI 등) 사용.
