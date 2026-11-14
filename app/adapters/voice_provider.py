"""Provider-independent speech contract, matching the public voice API."""
from abc import ABC, abstractmethod


class VoiceEngineError(Exception):
    """A speech provider could not produce a usable response."""


class IVoiceProvider(ABC):
    @property
    @abstractmethod
    def configured(self) -> bool:
        """Whether live speech transport is available."""

    @property
    @abstractmethod
    def cache_identity(self) -> str:
        """Non-secret provider/model/voice identity used to isolate cached audio."""

    @abstractmethod
    async def speech_to_text(
        self, audio_bytes: bytes, *, filename: str | None = None,
        language_code: str = "mr-IN", mode: str = "transcribe",
    ) -> dict: ...

    @abstractmethod
    async def text_to_speech(self, text: str, *, language_code: str = "mr-IN") -> dict: ...
