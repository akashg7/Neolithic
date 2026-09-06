from pydantic import BaseModel
from typing import Optional


class NarrateRequest(BaseModel):
    text: str
    language: str = "en"


class NarrateResponse(BaseModel):
    audio_url: str
    language: str


class TranscribeResponse(BaseModel):
    transcript: str
    language_code: Optional[str] = None
    request_id: Optional[str] = None


class CallInitiateRequest(BaseModel):
    offer_id: int


class CallInitiateResponse(BaseModel):
    call_session_id: int
    agora_token: Optional[str] = None
    channel_name: str
