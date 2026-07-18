from .data import MISSIONS


def start(mission_id: str) -> dict:
    s = MISSIONS[mission_id][0]
    return {
        "mission_id": mission_id,
        "step": s["step"],
        "prompt": s["prompt"],
        "options": s["options"],
        "hint": s["hint"],
    }


def handle_step(mission_id: str, current_step: int, action: str) -> dict:
    steps = MISSIONS[mission_id]
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
