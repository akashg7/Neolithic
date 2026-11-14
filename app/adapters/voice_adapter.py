"""Sarvam transport adapter preserving the existing voice JSON contract."""

import logging

import httpx

from app.config import settings
from app.adapters.voice_provider import IVoiceProvider, VoiceEngineError

logger = logging.getLogger(__name__)


class SarvamVoiceAdapter(IVoiceProvider):
    def __init__(self) -> None:
        # Read live from settings on each call, not once at import — tests and
        # env reloads mutate `settings.SARVAM_*` after the module loads.
        self.endpoint = settings.SARVAM_ASR_ENDPOINT
        self.model = settings.SARVAM_ASR_MODEL
        self.tts_endpoint = settings.SARVAM_TTS_ENDPOINT
        self.tts_speaker = settings.SARVAM_TTS_SPEAKER
        self.tts_model = "bulbul:v3"

    @property
    def api_key(self) -> str:
        return settings.SARVAM_API_KEY

    @property
    def configured(self) -> bool:
        """True when a Sarvam API key is present. The transcribe route should
        degrade gracefully (HTTP 503) rather than raise when it is absent."""
        return bool(self.api_key)

    @property
    def cache_identity(self) -> str:
        return f"sarvam:{self.tts_endpoint}:{self.tts_model}:{self.tts_speaker}"

    def _detect_format(self, audio_bytes: bytes, filename: str | None = None) -> tuple[str, str]:
        fn = (filename or "").lower()
        if fn.endswith(".mp3"):
            return "clip.mp3", "audio/mpeg"
        elif fn.endswith(".wav"):
            return "clip.wav", "audio/wav"
        elif fn.endswith(".m4a") or fn.endswith(".mp4"):
            return "clip.m4a", "audio/mp4"
        elif fn.endswith(".ogg") or fn.endswith(".opus"):
            return "clip.ogg", "audio/ogg"
        elif fn.endswith(".flac"):
            return "clip.flac", "audio/flac"
        elif fn.endswith(".aac"):
            return "clip.aac", "audio/aac"

        # Byte-sniffing fallback
        if audio_bytes.startswith(b"ID3") or audio_bytes[:2] in (b"\xff\xfb", b"\xff\xf3", b"\xff\xf2"):
            return "clip.mp3", "audio/mpeg"
        elif audio_bytes.startswith(b"RIFF"):
            return "clip.wav", "audio/wav"
        elif b"ftyp" in audio_bytes[:16]:
            return "clip.m4a", "audio/mp4"
        elif audio_bytes.startswith(b"OggS"):
            return "clip.ogg", "audio/ogg"

        return "clip.mp3", "audio/mpeg"

    async def speech_to_text(
        self,
        audio_bytes: bytes,
        *,
        filename: str | None = None,
        language_code: str = "mr-IN",
        mode: str = "transcribe",
    ) -> dict:
        """Proxy one audio clip to Sarvam STT. Returns
        `{transcript, language_code, request_id}` on success; raises
        `VoiceEngineError` on an upstream failure."""
        if not self.configured:
            raise VoiceEngineError("Sarvam API key is not configured (SARVAM_API_KEY)")

        upload_name, mime_type = self._detect_format(audio_bytes, filename)

        headers = {
            "api-subscription-key": self.api_key,
        }
        data = {
            "model": self.model,
            "language_code": language_code,
            "mode": mode,
        }
        files = {"file": (upload_name, audio_bytes, mime_type)}


        try:
            async with httpx.AsyncClient(timeout=30.0) as client:
                resp = await client.post(
                    self.endpoint,
                    headers=headers,
                    data=data,
                    files=files,
                )
        except httpx.HTTPError as exc:
            logger.warning("Sarvam STT transport error: %s", exc)
            raise VoiceEngineError(f"Upstream STT unreachable: {exc}") from exc

        if resp.status_code != 200:
            logger.warning(
                "Sarvam STT upstream error: status=%s body=%s",
                resp.status_code,
                resp.text[:300],
            )
            raise VoiceEngineError(
                f"Sarvam STT failed with HTTP {resp.status_code}: {resp.text[:200]}"
            )

        try:
            payload = resp.json()
        except ValueError as exc:
            raise VoiceEngineError("Sarvam STT returned invalid JSON") from exc
        if not isinstance(payload, dict):
            raise VoiceEngineError("Sarvam STT returned an invalid response")
        transcript = payload.get("transcript")
        if not isinstance(transcript, str):
            raise VoiceEngineError("Sarvam STT returned an invalid transcript")
        transcript = transcript.strip()
        if not transcript:
            raise VoiceEngineError("Sarvam STT returned an empty transcript")

        return {
            "transcript": transcript,
            "language_code": payload.get("language_code"),
            "request_id": payload.get("request_id"),
        }

    async def text_to_speech(
        self,
        text: str,
        *,
        language_code: str = "mr-IN",
    ) -> dict:
        """Synthesize Marathi speech for `text` via Sarvam TTS (bulbul:v3).

        Returns `{audio_base64, audio_format, request_id}` on success. Sarvam
        returns the audio as a base64-encoded WAV inside a JSON `audios`
        array; we return the raw base64 plus the format so the caller can
        decide whether to serve it as bytes or hand a data-URI to the client.

        The narration text is dynamic (a farmer's lot, dates, amounts), so it
        cannot be a pre-generated clip — this is the live TTS path the
        sale-window voice agent drives.
        """
        if not self.configured:
            raise VoiceEngineError("Sarvam API key is not configured (SARVAM_API_KEY)")
        if not text or not text.strip():
            raise VoiceEngineError("Cannot synthesize empty speech text")

        payload = {
            "inputs": [text.strip()],
            "target_language_code": language_code,
            "speaker": self.tts_speaker,
            "model": self.tts_model,
        }
        headers = {"api-subscription-key": self.api_key, "Content-Type": "application/json"}

        try:
            async with httpx.AsyncClient(timeout=30.0) as client:
                resp = await client.post(
                    self.tts_endpoint,
                    headers=headers,
                    json=payload,
                )
        except httpx.HTTPError as exc:
            logger.warning("Sarvam TTS transport error: %s", exc)
            raise VoiceEngineError(f"Upstream TTS unreachable: {exc}") from exc

        if resp.status_code != 200:
            logger.warning(
                "Sarvam TTS upstream error: status=%s body=%s",
                resp.status_code,
                resp.text[:300],
            )
            raise VoiceEngineError(
                f"Sarvam TTS failed with HTTP {resp.status_code}: {resp.text[:200]}"
            )

        try:
            payload_resp = resp.json()
        except ValueError as exc:
            raise VoiceEngineError("Sarvam TTS returned invalid JSON") from exc
        if not isinstance(payload_resp, dict):
            raise VoiceEngineError("Sarvam TTS returned an invalid response")
        audios = payload_resp.get("audios") or []
        audio_base64 = audios[0] if isinstance(audios, list) and audios else None
        if not isinstance(audio_base64, str) or not audio_base64:
            raise VoiceEngineError("Sarvam TTS returned an empty audio payload")

        return {
            "audio_base64": audio_base64,
            "audio_format": "wav",
            "request_id": payload_resp.get("request_id"),
            "language_code": language_code,
        }


class MockVoiceAdapter(IVoiceProvider):
    """Explicit offline/test provider; never selected silently in production."""
    configured = True
    cache_identity = "mock:pcm-wav:v1"

    async def speech_to_text(self, audio_bytes: bytes, *, filename=None,
                             language_code="mr-IN", mode="transcribe") -> dict:
        return {"transcript": "कांदा बाजार भाव काय आहे", "language_code": language_code,
                "request_id": None}

    async def text_to_speech(self, text: str, *, language_code="mr-IN") -> dict:
        import base64
        import io
        import wave
        out = io.BytesIO()
        with wave.open(out, "wb") as wav:
            wav.setnchannels(1)
            wav.setsampwidth(2)
            wav.setframerate(16000)
            wav.writeframes(b"\x00\x00" * 160)
        return {"audio_base64": base64.b64encode(out.getvalue()).decode(),
                "audio_format": "wav", "language_code": language_code, "request_id": None}
