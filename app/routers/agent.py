"""Agent FastAPI router: `/api/v1/agent/chat`, `/voice-chat`, and `/session/{id}`."""
from __future__ import annotations

import json
import logging
import uuid
from typing import Optional

from fastapi import APIRouter, Depends, File, Form, HTTPException, Request, UploadFile
from sqlalchemy.ext.asyncio import AsyncSession

from app.adapters.voice_provider import IVoiceProvider, VoiceEngineError
from app.agents.memory import SessionMemoryStore
from app.config import settings
from app.database import get_db
from app.dependencies.auth import get_optional_user
from app.dependencies.voice import get_voice_provider
from app.engines.agent_engine import AgentEngine, build_mock_response
from app.models.user import User
from app.schemas.agent import (
    AgentChatRequest,
    AgentChatResponse,
    ScreenContext,
    SessionDeleteResponse,
)

logger = logging.getLogger("krishi.agent.router")

router = APIRouter()

_MAX_AUDIO_BYTES = 25 * 1024 * 1024
_LOCALE_TO_SARVAM = {"mr": "mr-IN", "hi": "hi-IN", "en": "en-IN"}

_default_engine: Optional[AgentEngine] = None
_default_memory: Optional[SessionMemoryStore] = None


def get_agent_engine() -> AgentEngine:
    global _default_engine
    if _default_engine is None:
        _default_engine = AgentEngine()
    return _default_engine


def get_session_memory() -> SessionMemoryStore:
    global _default_memory
    if _default_memory is None:
        _default_memory = SessionMemoryStore()
    return _default_memory


async def _attach_tts(
    response: AgentChatResponse,
    *,
    locale: str,
    include_audio: bool,
    voice_provider: Optional[IVoiceProvider],
) -> AgentChatResponse:
    if not include_audio or voice_provider is None or not response.reply_text:
        return response
    if not getattr(voice_provider, "configured", False):
        return response
    try:
        tts = await voice_provider.text_to_speech(
            response.reply_text,
            language_code=_LOCALE_TO_SARVAM.get(locale, "mr-IN"),
        )
        response.audio_base64 = tts.get("audio_base64")
    except VoiceEngineError as exc:
        logger.warning("Agent TTS synthesis skipped: %s", exc)
    except Exception as exc:
        logger.warning("Agent TTS synthesis failed unexpectedly: %s", exc)
    return response


def _parse_screen_context(raw: str) -> ScreenContext:
    if not raw or not raw.strip():
        return ScreenContext()
    try:
        data = json.loads(raw)
        return ScreenContext.model_validate(data if isinstance(data, dict) else {})
    except Exception:
        return ScreenContext()


async def _extract_audio_bytes(
    request: Request,
    audio: Optional[UploadFile],
    file: Optional[UploadFile],
) -> Optional[bytes]:
    upload = audio if audio is not None else file
    if upload is not None:
        data = await upload.read()
        if data:
            return data
    try:
        form = await request.form()
        for _, val in form.items():
            if isinstance(val, UploadFile):
                data = await val.read()
                if data:
                    return data
    except Exception:
        pass
    return None


@router.post("/chat", response_model=AgentChatResponse)
async def agent_chat(
    payload: AgentChatRequest,
    db: AsyncSession = Depends(get_db),
    user: Optional[User] = Depends(get_optional_user),
    engine: AgentEngine = Depends(get_agent_engine),
    voice_provider: IVoiceProvider = Depends(get_voice_provider),
) -> AgentChatResponse:
    """Conversational text turn with optional TTS audio output."""
    if settings.AGENT_MOCK:
        resp = build_mock_response(
            session_id=payload.session_id,
            turn_id=f"turn_{uuid.uuid4().hex[:12]}",
            message=payload.message,
            locale=payload.locale,
            screen_context=payload.screen_context,
        )
        return await _attach_tts(
            resp,
            locale=payload.locale,
            include_audio=payload.include_audio,
            voice_provider=voice_provider,
        )

    resp = await engine.run_turn(
        db=db,
        user=user,
        session_id=payload.session_id,
        locale=payload.locale,
        screen_context=payload.screen_context,
        text=payload.message,
    )
    return await _attach_tts(
        resp,
        locale=payload.locale,
        include_audio=payload.include_audio,
        voice_provider=voice_provider,
    )


@router.post("/voice-chat", response_model=AgentChatResponse)
async def agent_voice_chat(
    request: Request,
    session_id: str = Form(..., min_length=1, max_length=128),
    locale: str = Form("mr"),
    screen_context: str = Form("{}"),
    include_audio: bool = Form(True),
    audio: Optional[UploadFile] = File(None),
    file: Optional[UploadFile] = File(None),
    db: AsyncSession = Depends(get_db),
    user: Optional[User] = Depends(get_optional_user),
    engine: AgentEngine = Depends(get_agent_engine),
    voice_provider: IVoiceProvider = Depends(get_voice_provider),
) -> AgentChatResponse:
    """Single round-trip voice turn: parallel Sarvam STT -> Agent loop -> optional TTS."""
    raw_audio = await _extract_audio_bytes(request, audio, file)
    if not raw_audio:
        raise HTTPException(
            status_code=422,
            detail="Missing audio file — attach audio under form field 'audio' or 'file'.",
        )
    if len(raw_audio) > _MAX_AUDIO_BYTES:
        raise HTTPException(status_code=413, detail="Audio clip too large (max 25MB).")

    norm_locale = locale if locale in ("mr", "hi", "en") else "mr"
    parsed_screen = _parse_screen_context(screen_context)

    if settings.AGENT_MOCK:
        resp = build_mock_response(
            session_id=session_id,
            turn_id=f"turn_{uuid.uuid4().hex[:12]}",
            message="माझ्याकडे २० बोरी कांदा आहे, लासलगावला कधी विकू?",
            locale=norm_locale,
            screen_context=parsed_screen,
        )
        return await _attach_tts(
            resp,
            locale=norm_locale,
            include_audio=include_audio,
            voice_provider=voice_provider,
        )

    resp = await engine.run_turn(
        db=db,
        user=user,
        session_id=session_id,
        locale=norm_locale,
        screen_context=parsed_screen,
        audio=raw_audio,
    )
    return await _attach_tts(
        resp,
        locale=norm_locale,
        include_audio=include_audio,
        voice_provider=voice_provider,
    )


@router.delete("/session/{session_id}", response_model=SessionDeleteResponse)
async def clear_agent_session(
    session_id: str,
    memory: SessionMemoryStore = Depends(get_session_memory),
) -> SessionDeleteResponse:
    """Clear Redis conversation memory for a session."""
    cleared = await memory.clear_session(session_id)
    return SessionDeleteResponse(ok=True, session_id=session_id, cleared=cleared)
