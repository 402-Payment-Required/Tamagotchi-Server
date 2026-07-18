# 손주 서버 (Tamagotchi-Server)

고령층 디지털 소외 해소 앱 "손주"의 백엔드 API 서버.
AI 손주와 **음성으로 대화**하고 **미션**을 수행하는 흐름을 제공한다.

## 기술 스택

- Python 3.11 · FastAPI · uvicorn · SQLite
- STT: [faster-whisper](https://github.com/SYSTRAN/faster-whisper) base (CPU int8)
- LLM: Anthropic **Claude Haiku 4.5** (`claude-haiku-4-5`) — 이 브랜치 기준
- TTS: [Piper-TTS](https://github.com/rhasspy/piper) 한국어 low 티어

**브랜치별 스택**:
- `main`: Claude API + faster-whisper base + Piper (경량 최적화)
- `feat/ai-lightweight`: 위와 동일 (별도 개발/테스트용)
- `feat/ai-pipeline`: Ollama exaone3.5 + MeloTTS (오프라인/저비용 우선)

## 빠른 실행 (Windows / macOS / Linux 공통)

```bash
# 1. Claude API 키 설정 (.env는 자동 로드됨)
cp server/.env.example server/.env
# .env 편집 → ANTHROPIC_API_KEY=sk-ant-...

# 2. 의존성 설치
cd server
uv sync

# 3. MeCab-ko 사전 다운로드 (전 플랫폼)
uv run python -m unidic download

# 4. 서버 실행
uv run uvicorn main:app --host 0.0.0.0 --port 8000
```

Swagger UI: <http://localhost:8000/docs>

### 플랫폼별 참고

- **Windows**: `chat/__init__.py`가 MeCab/eunjeon 호환 shim을 자동 주입 (Visual C++ 빌드 없이도 g2pkk 동작)
- **macOS / Linux**: 별도 셔임 불필요, `python-mecab-ko`가 정상 작동
- **API 키가 없어도**: 서버는 정상 기동. `/voice/chat`/`/chat` 호출 시 fallback 응답(무음 WAV + 안내 문구) 반환

## 개발용 (모델·API 키 없이 즉시 실행)

```bash
cd server
uv run python run_dev.py   # STT/LLM/TTS 모두 Mock 주입, port 8000
uv run python test_api.py  # HTTP 엔드포인트 검증 (19/19)
```

## API 요약

| 그룹 | 엔드포인트 | 설명 |
|---|---|---|
| 음성 | `POST /voice/start`, `/voice/chat`, `/voice/end` | 세션 발급 → STT+LLM+TTS 왕복 → 종료 |
| 미션 | `GET /mission/list`, `POST /mission/{start,step,complete}` | 키오스크·문자·SMS 미션 |
| 챗봇 | `POST /chat` | 텍스트 챗봇 (요청당 세션) |
| 리포트 | `GET /report` | 감정·신호 이력 |

자세한 요청·응답 스키마는 `server/schemas.py` 또는 Swagger 참고.

## 브랜치별 스택 비교

| 항목 | `feat/ai-pipeline` | `main`/`feat/ai-lightweight` |
|---|---|---|
| LLM | Ollama exaone3.5 (로컬) | Claude Haiku 4.5 (API) |
| STT | faster-whisper medium | faster-whisper **base** |
| TTS | MeloTTS-Korean | Piper-TTS **low** |
| 배포 크기 | ~1.5GB (Ollama 포함) | **~500MB** (모델만) |
| 인터넷 필요 | 아니오 | 예 (API 호출) |
| RAM 사용 | 5.4 GB (Ollama daemon) | ~800MB |
| 요청당 비용 | 무료 | ~1.6원 (Claude Haiku) |

- **오프라인·저비용 우선** → `feat/ai-pipeline`
- **경량 배포·빠른 응답** → `main` (권장)

## 견고성

`server/test_robustness.py` — 다음 시나리오에서 앱이 죽지 않음을 자동 검증:

- API key 미설정 / 잘못된 key
- 클라이언트 요청 도중 disconnect (Claude 요청도 즉시 취소, 토큰 낭비 없음)
- Claude 응답 지연 → 30초 timeout → fallback
- SDK 자동 재시도 차단 (`max_retries=0`)
- 깨진 오디오 업로드 → silent WAV fallback
