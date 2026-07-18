from fastapi import HTTPException

from .data import MISSIONS


def _get_steps(mission_id: str) -> list:
    if mission_id not in MISSIONS:
        raise HTTPException(status_code=404, detail=f"미션을 찾을 수 없습니다: {mission_id}")
    return MISSIONS[mission_id]


def start(mission_id: str) -> dict:
    steps = _get_steps(mission_id)
    s = steps[0]
    return {
        "mission_id": mission_id,
        "step": s["step"],
        "prompt": s["prompt"],
        "options": s["options"],
        "hint": s["hint"],
    }


def handle_step(mission_id: str, current_step: int, action: str) -> dict:
    steps = _get_steps(mission_id)
    if current_step >= len(steps):
        current_step = len(steps) - 1
    cur = steps[current_step]
    if action == cur["answer"]:
        if cur.get("final"):
            return {"correct": True, "done": True, "message": "완료했어요! 잘하셨어요 🎉"}
        nxt = steps[current_step + 1]
        return {
            "correct": True,
            "done": False,
            "step": nxt["step"],
            "prompt": nxt["prompt"],
            "options": nxt["options"],
            "hint": nxt["hint"],
        }
    return {
        "correct": False,
        "done": False,
        "step": cur["step"],
        "prompt": cur["prompt"],
        "options": cur["options"],
        "hint": cur["hint"],
    }
