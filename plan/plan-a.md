# PLAN — A 담당 (AI) · 서버 기준

> 소유: `server/chat/engine.py`, `server/chat/prompts.py`
> 책임: 손주 대사 + 감정 + 시그널을 한 JSON으로 만드는 `chat()` 함수.
> B가 이 함수를 `/chat` 라우터에서 import한다. 너는 서버 라우팅·DB·프론트를 건드리지 않는다.

---

## 산출물

1. `chat/prompts.py` — 손주 페르소나 시스템 프롬프트
2. `chat/engine.py` — `chat(message, history=None) -> {reply, emotion, signals}`

## 완료 정의 (Definition of Done)

- [ ] 텍스트 메시지 → `{reply, emotion, signals}` JSON 안정적 반환
- [ ] emotion 5종 정확히 판정
- [ ] signals(meal/mood 등) 추출
- [ ] JSON 파싱 실패 시 폴백(neutral) — 서버가 500 안 던짐
- [ ] 응답 5초 이내
- [ ] 실제 발화 10개로 튜닝 완료

---

## 타임라인

### 0~1h · 공동 셋업 + 계약 확인
- 셋이 `main.py`/`db.py`/`schemas.py` 뼈대 완성(냉동)에 참여.
- `chat()` 반환 JSON = `schemas.py`의 `/chat` 응답과 100% 일치 확인.
- emotion 5종 값, history 전달 여부, 모델 스트링 확정.

### 1~2h · Mock 걷어낼 준비 + 프롬프트 초안
- `prompts.py`에 손주 페르소나 시스템 프롬프트 작성(문서 5의 초안 사용).
- B가 Mock으로 프론트 붙이는 동안, 너는 프롬프트에 집중.

### 2~6h · engine.py 구현
- Anthropic SDK로 `chat()` 구현.
- JSON 강제 출력 + 파싱 + 검증 + 폴백.
- 로컬에서 단독 테스트(서버 없이 함수만 호출).

```python
# 단독 테스트 예
from chat.engine import chat
print(chat("오늘 아무것도 안 먹었어"))
# → {'reply': '...', 'emotion': 'worried', 'signals': {'meal': False}}
```

### 6~9h · 튜닝
- 발화 10종 테이블로 감정·시그널 정확도 점검(문서 5 참조).
- 손주다움(안부를 '조르는' 말투) 강화. 점검하듯 묻는 톤이 나오면 프롬프트 수정.
- JSON 깨지면 "출력 형식" 지시를 예시와 함께 강화.

### 9~12h · 통합 지원
- B가 `/chat`에 `chat()` 연결. 실제 앱→서버→Claude 전 구간 확인.
- 지연이 크면 max_tokens·프롬프트 길이 줄여 최적화.

### 12~14h · 데모 대비
- 데모 시나리오에서 심사위원이 할 법한 말 5개 미리 돌려보고 어색한 응답 교정.
- (여유) C의 키오스크 힌트 문구 톤 감수.

### 14~16h · 마무리
- 프롬프트 최종 고정. 이후 수정 금지(변경이 데모를 깰 수 있음).

---

## 리스크 & 대비

| 리스크 | 대비 |
|---|---|
| JSON 형식 깨짐 | 프롬프트에 출력 예시 2~3개 명시, 파싱 폴백 |
| 감정 오판(항상 happy) | 튜닝 테이블로 worried/sad 케이스 강제 확인 |
| 응답 지연 | max_tokens 축소, history 최소화 |
| 모델 스트링 오류 | 0시에 콘솔에서 검증 후 확정 |

## 접점

- A → B: `chat()` 함수 (import). 반환 JSON이 계약과 일치하면 끝.
- A ↛ C: 직접 접점 없음(선택적으로 힌트 톤 감수만).
- 절대 하지 말 것: 라우터/DB/스키마 수정, 계약 형식 변경.