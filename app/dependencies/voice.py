"""Member 5 voice composition root; replace this dependency for another vendor."""
from functools import lru_cache
from pathlib import Path
import tempfile

from app.adapters.cached_voice_decorator import CachedVoiceDecorator
from app.adapters.voice_provider import IVoiceProvider
from app.config import settings
from app.engines.voice_engine import voice_engine


@lru_cache(maxsize=1)
def _cached_provider() -> CachedVoiceDecorator:
    # Outside the repository; no generated audio or user text enters source control.
    return CachedVoiceDecorator(voice_engine, Path(tempfile.gettempdir()) / "krishi-mitr-voice")


def get_voice_provider() -> IVoiceProvider:
    return _cached_provider() if settings.VOICE_CACHE_ENABLED else voice_engine
