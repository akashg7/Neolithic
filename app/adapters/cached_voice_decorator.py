"""Disk-backed TTS decorator; caches usable audio, never provider errors."""
import asyncio
import base64
import hashlib
import json
import logging
import os
from pathlib import Path
import tempfile

from app.adapters.voice_provider import IVoiceProvider

logger = logging.getLogger(__name__)


class CachedVoiceDecorator(IVoiceProvider):
    def __init__(self, wrapped: IVoiceProvider, cache_dir: str | Path):
        self.wrapped = wrapped
        self.cache_dir = Path(cache_dir)

    @property
    def configured(self) -> bool:
        return self.wrapped.configured

    @property
    def cache_identity(self) -> str:
        return self.wrapped.cache_identity

    def _path(self, text: str, language_code: str) -> Path:
        key = json.dumps([self.cache_identity, language_code, text], ensure_ascii=False)
        return self.cache_dir / (hashlib.sha256(key.encode()).hexdigest() + ".json")

    @staticmethod
    def _valid(result) -> bool:
        if not isinstance(result, dict) or result.get("audio_format") != "wav":
            return False
        try:
            raw = base64.b64decode(result["audio_base64"], validate=True)
            return raw.startswith(b"RIFF") and raw[8:12] == b"WAVE"
        except (ValueError, KeyError, TypeError):
            return False

    def _read(self, path: Path) -> dict | None:
        try:
            result = json.loads(path.read_text())
            return result if self._valid(result) else None
        except (OSError, ValueError, TypeError):
            return None

    def _write(self, path: Path, result: dict) -> None:
        temporary = None
        try:
            path.parent.mkdir(mode=0o700, parents=True, exist_ok=True)
            with tempfile.NamedTemporaryFile(mode="w", dir=path.parent, delete=False) as f:
                temporary = f.name
                json.dump(result, f)
            os.replace(temporary, path)
        except OSError:
            # Cache availability must not turn successful synthesis into an error.
            logger.warning("Voice cache write failed", exc_info=True)
        finally:
            if temporary is not None:
                try:
                    os.unlink(temporary)
                except OSError:
                    pass

    async def speech_to_text(self, audio_bytes: bytes, *, filename=None,
                             language_code="mr-IN", mode="transcribe") -> dict:
        return await self.wrapped.speech_to_text(
            audio_bytes, filename=filename, language_code=language_code, mode=mode,
        )

    async def text_to_speech(self, text: str, *, language_code="mr-IN") -> dict:
        path = self._path(text, language_code)
        cached = await asyncio.to_thread(self._read, path)
        if cached is not None:
            return cached
        result = await self.wrapped.text_to_speech(text, language_code=language_code)
        if self._valid(result):
            await asyncio.to_thread(self._write, path, result)
        return result
