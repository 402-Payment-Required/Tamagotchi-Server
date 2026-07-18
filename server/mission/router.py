from fastapi import APIRouter, HTTPException

from db import get_progress, list_progress, upsert_progress
from schemas import (
    MissionCompleteRequest,
    MissionCompleteResponse,
    MissionListResponse,
    MissionStartRequest,
    MissionStartResponse,
    MissionStepRequest,
    MissionStepResponse,
)

from . import service
from .data import MISSION_META, MISSIONS

router = APIRouter(prefix="/mission")


def _ensure_mission(mission_id: str) -> None:
    if mission_id not in MISSIONS:
        raise HTTPException(status_code=404, detail=f"unknown mission_id: {mission_id}")


@router.get("/list", response_model=MissionListResponse)
def list_missions(user_id: str):
    progress = list_progress(user_id)
    missions = [
        {
            "mission_id": mission_id,
            "title": meta["title"],
            "type": meta["type"],
            "status": progress[mission_id]["status"] if mission_id in progress else "locked",
        }
        for mission_id, meta in MISSION_META.items()
    ]
    return {"missions": missions}


@router.post("/start", response_model=MissionStartResponse)
def start(body: MissionStartRequest):
    _ensure_mission(body.mission_id)
    upsert_progress(body.user_id, body.mission_id, "inprogress", 0)
    return service.start(body.mission_id)


@router.post("/step", response_model=MissionStepResponse)
def step(body: MissionStepRequest):
    _ensure_mission(body.mission_id)
    progress = get_progress(body.user_id, body.mission_id)
    current_step = progress["current_step"] if progress else 0
    # DB에 저장된 current_step이 실제 미션 스텝 범위를 벗어난 경우 (스키마 변경 등) 0으로 리셋
    if current_step < 0 or current_step >= len(MISSIONS[body.mission_id]):
        current_step = 0
    result = service.handle_step(body.mission_id, current_step, body.action)
    if result["correct"]:
        if result["done"]:
            upsert_progress(body.user_id, body.mission_id, "done", current_step)
        else:
            upsert_progress(body.user_id, body.mission_id, "inprogress", result["step"])
    return result


@router.post("/complete", response_model=MissionCompleteResponse)
def complete(body: MissionCompleteRequest):
    upsert_progress(body.user_id, body.mission_id, "done", -1)
    return {"mission_id": body.mission_id, "status": "done"}
