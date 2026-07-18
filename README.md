# 손주 서버 (Tamagotchi-Server)

고령층 디지털 소외 해소 앱 "손주"의 백엔드 API 서버.
AI 손주와 **음성으로 대화**하고 **미션**을 수행하는 흐름을 제공한다.

## 기술 스택

- Python 3.11 · FastAPI · uvicorn · SQLite
- STT: [faster-whisper](https://github.com/SYSTRAN/faster-whisper) medium (CPU int8)
- LLM: [Ollama](https://ollama.com/) exaone3.5:7.8b
- TTS: [MeloTTS-Korean](https://github.com/myshell-ai/MeloTTS)

## 빠른 실행

```bash
# 1. Ollama 설치 후 모델 pull
ollama pull exaone3.5:7.8b

# 2. 의존성 설치
cd server
uv sync

# 3. (Windows만) MeCab-ko 사전 다운로드
uv run python -m unidic download

# 4. 서버 실행
uv run uvicorn main:app --host 0.0.0.0 --port 8000
```

Swagger UI: <http://localhost:8000/docs>

## 개발용 (모델 없이 즉시 실행)

```bash
cd server
uv run python run_dev.py   # AI 모듈 Mock 주입, port 8000
uv run python test_api.py  # 모든 HTTP 엔드포인트 검증 (19/19)
```

## API 요약

| 그룹 | 엔드포인트 | 설명 |
|---|---|---|
| 음성 | `POST /voice/start`, `/voice/chat`, `/voice/end` | 세션 발급 → STT+LLM+TTS 왕복 → 종료 |
| 미션 | `GET /mission/list`, `POST /mission/{start,step,complete}` | 키오스크·문자·SMS 미션 |
| 챗봇 | `POST /chat` | 텍스트 챗봇 (요청당 세션) |
| 리포트 | `GET /report` | 감정·신호 이력 |

자세한 요청·응답 스키마는 `server/schemas.py` 또는 Swagger 참고.
