from typing import Literal, Optional

from pydantic import BaseModel

Emotion = Literal["happy", "worried", "excited", "sad", "neutral"]
MissionType = Literal["kiosk", "typing", "sms"]
MissionStatus = Literal["locked", "inprogress", "done"]


class ChatRequest(BaseModel):
    user_id: str
    message: str


class ChatResponse(BaseModel):
    reply: str
    emotion: Emotion
    signals: dict = {}


class MissionItem(BaseModel):
    mission_id: str
    title: str
    type: MissionType
    status: MissionStatus


class MissionListResponse(BaseModel):
    missions: list[MissionItem]


class MissionStartRequest(BaseModel):
    user_id: str
    mission_id: str


class MissionStartResponse(BaseModel):
    mission_id: str
    step: int
    prompt: str
    options: list[str]
    hint: str


class MissionStepRequest(BaseModel):
    user_id: str
    mission_id: str
    action: str


class MissionStepResponse(BaseModel):
    correct: bool
    done: bool
    step: Optional[int] = None
    prompt: Optional[str] = None
    options: Optional[list[str]] = None
    hint: Optional[str] = None
    message: Optional[str] = None


class MissionCompleteRequest(BaseModel):
    user_id: str
    mission_id: str


class MissionCompleteResponse(BaseModel):
    mission_id: str
    status: MissionStatus


class VoiceStartRequest(BaseModel):
    user_id: str


class VoiceStartResponse(BaseModel):
    session_id: str


class VoiceChatResponse(BaseModel):
    audio: str  # base64 encoded WAV
    reply: str
    emotion: Emotion
    signals: dict = {}


class VoiceEndRequest(BaseModel):
    user_id: str
    session_id: str


class VoiceEndResponse(BaseModel):
    status: str
