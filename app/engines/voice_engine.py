"""Compatibility entry point for existing voice-engine callers.

Transport lives in the Sarvam adapter; routers consume IVoiceProvider through
FastAPI dependency injection. Device speech remains the offline fallback.
"""
import httpx  # Compatibility for existing callers/tests patching this module.

from app.adapters.voice_adapter import SarvamVoiceAdapter
from app.adapters.voice_provider import VoiceEngineError


class VoiceEngine(SarvamVoiceAdapter):
    """Backward-compatible name for the Sarvam adapter."""


voice_engine = VoiceEngine()
