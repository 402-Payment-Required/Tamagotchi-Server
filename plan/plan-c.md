# PLAN — C 담당 (Mission) · 서버 기준

> 소유: `server/mission/` 전부, DB의 `mission_progress`
> 책임: 대화와 분리된 미션(키오스크·타자)의 서버 로직 전체.
> (앱 미션 화면은 별도 문서 7 참조 — 이 플랜은 서버 파트만 다룬다.)
> 미션은 `/chat`을 호출하지 않는 독립 기능 → 너는 A·B와 거의 안 얽혀 가장 자유롭게 달린다.

---

## 산출물

1. `mission/router.py` — `/mission/list`, `/start`, `/step`, `/complete`
2. `mission/service.py` — 키오스크 상태머신, 타자 판정
3. `mission/data.py` — 미션 정의(단계·선택지·정답·힌트)
4. `db.py`의 `mission_progress` CRUD (헬퍼는 mission 쪽에 둬도 됨)

## 완료 정의 (Definition of Done)

- [ ] `/mission/list`가 상태(locked/inprogress/done) 반환
- [ ] `/mission/start`가 첫 단계 반환
- [ ] `/mission/step`이 정답→다음단계 / 오답→힌트 판정
- [ ] `/mission/complete`가 done 처리
- [ ] 키오스크 카페 주문 1개 완주 가능
- [ ] 타자 연습 1개 판정 동작

---

## 타임라인

### 0~1h · 공동 셋업 참여
- `main.py`에 mission 라우터 등록될 자리 B와 확인.
- `schemas.py`의 `/mission/*` 계약 확인(문서 4).
- `mission_progress` 테이블 init이 `db.py`에 있는지 확인.

### 1~9h · 미션 서버 통째 구현 (독립적으로 쭉)
Mock 필요 없음 — 계약만 있으면 바로 자체 완결로 개발 가능.

1. `mission/data.py`에 키오스크 카페 6단계 정의(문서 7 초안).
2. `mission/service.py`에 판정 로직:
   - `start(mission_id)` → 0단계 반환
   - `handle_step(mission_id, current_step, action)` → 정답/오답 분기
   - `complete(mission_id)` → done
3. `mission/router.py`에 4개 엔드포인트 래핑 + `mission_progress` 갱신.
4. 이 구간 안에 **키오스크 1개 완주**가 서버에서 되게. (프론트 없이 curl로 검증)

```bash
# curl 검증 예
curl -X POST localhost:8000/mission/start -H 'Content-Type: application/json' \
  -d '{"user_id":"t","mission_id":"kiosk_cafe"}'
curl -X POST localhost:8000/mission/step -H 'Content-Type: application/json' \
  -d '{"user_id":"t","mission_id":"kiosk_cafe","action":"eat_in"}'
```

### 9~12h · 통합 + 타자 미션
- 앱(문서 7 화면)과 연결, 실제 폰에서 키오스크 완주 확인.
- 타자·문자 미션(`typing_1`) 추가: 제시 문장 판정.

### 12h~ · 데모 대비
- 데모 경로(키오스크 완주 + 오답→힌트 1회) 리허설.
- 힌트 문구 톤 어색하면 A에게 감수 요청(선택).

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

## router.py 스케치

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
    # 현재 step을 DB에서 읽고 판정, 결과에 따라 current_step/ status 갱신
    ...
    return service.handle_step(body["mission_id"], current_step, body["action"])
```

> `mission_progress` 읽고/쓰는 헬퍼는 `db.py`에 추가하거나 mission 내부에 둔다. B의 users/signals는 건드리지 않는다.

---

## 리스크 & 대비

| 리스크 | 대비 |
|---|---|
| 단계 상태 꼬임(현재 step 추적) | DB의 current_step를 단일 진실로. 프론트가 임의로 안 보냄 |
| 키오스크 UI가 진짜 같지 않음 | 실제 카페 키오스크 스샷 참고, 큰 버튼·명확한 색 |
| 시간 부족 | 키오스크 1개만 완벽히, 타자는 여유 시 |

## 접점 (최소)

- C → B: `main.py`에 mission 라우터 등록(자리는 B가 확보).
- C ↛ A: 대화 서버 호출 안 함. 힌트는 고정 문구(A 톤 감수는 선택).
- C가 유일하게 쓰는 공유 자원: `mission_progress` 테이블. users/signals는 안 건드림.