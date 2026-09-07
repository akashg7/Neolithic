from pydantic import BaseModel
from typing import Optional


class NarrateRequest(BaseModel):
    text: str
    locale: str = "mr"


class NarrateResponse(BaseModel):
    audio_base64: str
    audio_format: str = "wav"
    language_code: str = "mr-IN"
    request_id: Optional[str] = None


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
