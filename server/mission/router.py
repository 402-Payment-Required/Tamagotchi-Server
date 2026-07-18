from fastapi import APIRouter

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
from .data import MISSION_META

router = APIRouter(prefix="/mission")


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
    upsert_progress(body.user_id, body.mission_id, "inprogress", 0)
    return service.start(body.mission_id)


@router.post("/step", response_model=MissionStepResponse)
def step(body: MissionStepRequest):
    progress = get_progress(body.user_id, body.mission_id)
    current_step = progress["current_step"] if progress else 0
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
