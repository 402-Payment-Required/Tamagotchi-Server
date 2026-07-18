# PLAN — A 담당 (AI) · 서버 기준

> 소유: `server/chat/engine.py`, `server/chat/prompts.py`, `server/chat/stt.py`, `server/chat/tts.py`, `server/chat/session.py`
> 책임: 음성 입력 → STT → LLM 응답 → TTS 음성 출력 파이프라인 전체.
> Backend(B)가 이 파이프라인을 `/voice/*` 라우터에서 호출한다. 라우터·DB·스키마는 건드리지 않는다.

---

## 기술 스택

| 역할 | 선택 | 비고 |
|---|---|---|
| STT | faster-whisper (medium) | 로컬, GPU 없는 환경 기준 |
| LLM | Ollama exaone3.5:7.8b | 로컬, `localhost:11434` |
| TTS | MeloTTS-Korean | 로컬 |
| 실행 환경 | 로컬 컴퓨터 시뮬레이션 | 모바일 앱 아님 |
| 인터페이스 | 웹 서비스 | 프론트는 별도 담당 |

---

## 산출물

1. `chat/stt.py` — faster-whisper medium 래퍼: `transcribe(audio_bytes) -> str`
2. `chat/tts.py` — MeloTTS-Korean 래퍼: `synthesize(text) -> bytes`
3. `chat/session.py` — 세션별 히스토리 in-memory 관리
4. `chat/prompts.py` — 손주 페르소나 시스템 프롬프트 (exaone3.5 형식)
5. `chat/engine.py` — Ollama 멀티턴 호출: `chat(message, session_id) -> {reply, emotion, signals}`

---

## Backend에 전달할 API 계약 (변경사항)

### POST /voice/start
```
요청: { "user_id": str }
응답: { "session_id": str }
```
- 세션 생성, 히스토리 초기화.

### POST /voice/chat
```
요청: multipart/form-data { user_id: str, session_id: str, audio: File }
응답: { "audio": str(base64), "reply": str, "emotion": str, "signals": object }
```
- audio → STT → LLM → TTS 전 파이프라인 처리.
- emotion ∈ {happy, worried, excited, sad, neutral}

### POST /voice/end
```
요청: { "user_id": str, "session_id": str }
응답: { "status": "ended" }
```
- 세션 종료, 히스토리 정리.
- 프론트가 무음 타임아웃 또는 종료 버튼 시 호출.

> 기존 텍스트 `/chat`은 Backend 판단에 따라 유지 또는 제거.

---

## 대화 흐름

```
[시작 버튼] → POST /voice/start → session_id 발급
    ↓
[녹음 중]
    ↓  (무음 타임아웃 또는 종료 버튼)
POST /voice/chat (audio 전송)
    → STT (faster-whisper) → 텍스트
    → Ollama exaone3.5 (히스토리 포함) → {reply, emotion, signals}
    → MeloTTS → 오디오 bytes
    → 응답 반환
    ↓
[프론트 오디오 재생 → 다시 녹음 대기]
    ↓  (종료 버튼 또는 타임아웃)
POST /voice/end → 세션 종료
```

---

## 완료 정의 (Definition of Done)

- [ ] `transcribe(audio_bytes)` → 한국어 텍스트 안정적 반환
- [ ] `synthesize(text)` → 재생 가능한 오디오 bytes 반환
- [ ] 세션별 히스토리 누적, 멀티턴 대화 가능
- [ ] emotion 5종 정확히 판정
- [ ] signals(meal/mood 등) 추출
- [ ] JSON 파싱 실패 시 폴백(neutral) — 서버 500 안 던짐
- [ ] 응답 (STT+LLM+TTS) 10초 이내
- [ ] 발화 10개로 감정·시그널 튜닝 완료

---

## 파일별 역할

### `chat/stt.py`
```python
# faster-whisper medium 로드 (최초 1회)
# transcribe(audio_bytes: bytes) -> str
```

### `chat/tts.py`
```python
# MeloTTS-Korean 로드 (최초 1회)
# synthesize(text: str) -> bytes  (WAV or MP3)
```

### `chat/session.py`
```python
# sessions: dict[session_id, list[messages]]
# start_session(user_id) -> session_id
# get_history(session_id) -> list
# add_turn(session_id, role, content)
# end_session(session_id)
```

### `chat/engine.py`
```python
# Ollama HTTP API (localhost:11434)
# chat(message: str, session_id: str) -> {reply, emotion, signals}
# 히스토리 포함 멀티턴, JSON 강제 출력, 폴백 처리
```

### `chat/prompts.py`
```python
# SYSTEM_PROMPT: exaone3.5 형식, 손주 페르소나
# JSON 출력 강제 (예시 3개 포함)
```

---

## 구현 순서

1. `requirements.txt` 업데이트 (faster-whisper, MeloTTS, ollama)
2. `chat/session.py` — 세션 관리
3. `chat/stt.py` — faster-whisper medium 래퍼
4. `chat/tts.py` — MeloTTS-Korean 래퍼
5. `chat/prompts.py` — exaone3.5 형식 프롬프트
6. `chat/engine.py` — Ollama 멀티턴 교체
7. 단독 테스트 (파이프라인 함수만 직접 호출)
8. Backend에 계약 전달 → 통합 테스트

### 단독 테스트 예
```python
# STT
from chat.stt import transcribe
with open("test.wav", "rb") as f:
    print(transcribe(f.read()))

# Engine
from chat.session import start_session
from chat.engine import chat
sid = start_session("user_1")
print(chat("오늘 아무것도 안 먹었어", sid))
# → {'reply': '...', 'emotion': 'worried', 'signals': {'meal': False}}

# TTS
from chat.tts import synthesize
audio = synthesize("할머니 밥은 챙겨 드셔야죠!")
with open("out.wav", "wb") as f:
    f.write(audio)
```

---

## 리스크 & 대비

| 리스크 | 대비 |
|---|---|
| faster-whisper 첫 로드 느림 | 서버 시작 시 모델 프리로드, 요청마다 재로드 금지 |
| MeloTTS 한국어 발음 부자연 | 발화 10개 사전 검증, 필요시 속도·피치 파라미터 조정 |
| Ollama JSON 형식 깨짐 | 프롬프트에 출력 예시 3개 명시, 파싱 폴백 |
| 감정 오판(항상 happy) | 튜닝 테이블로 worried/sad 케이스 강제 확인 |
| 전체 파이프라인 지연 10초 초과 | STT·TTS 모델 프리로드, max_tokens 최소화 |
| Ollama 서버 미실행 | 시작 시 연결 확인, 실패 시 명확한 에러 메시지 |

---

## 접점

- A → Backend: `transcribe()`, `synthesize()`, `chat()` 함수 + `/voice/*` 계약.
- A ↛ mission: 직접 접점 없음.
- 절대 하지 말 것: 라우터/DB/스키마 수정, 계약 형식 변경.
