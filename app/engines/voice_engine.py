"""
Voice Engine — Sarvam AI speech-to-text (STT) proxy.

The mobile app (`VoiceMic`) records a clip and POSTs it to our
`POST /api/v1/voice/transcribe`; this engine proxies the audio to Sarvam's
`/speech-to-text` REST endpoint and returns the transcript.

★ Why a proxy and not a direct client call?
  - The Sarvam API key never ships on the device. The app holds no secrets
    (config.ts I10) — the key lives here, server-side, in `settings`.
  - One place to enforce auth (our JWT), rate limiting, and to swap the
    upstream model/language without a frontend release.

★ Upstream contract (docs.sarvam.ai/api-reference/speech-to-text/transcribe):
  POST https://api.sarvam.ai/speech-to-text
  Auth header:  `api-subscription-key: <key>`
  Body:         multipart/form-data with fields:
                  file          — the audio (WAV/MP3/AAC/M4A/OGG…)
                  model         — "saaras:v3" (default)
                  language_code — "mr-IN" etc., or "unknown" to auto-detect
                  mode          — "transcribe" (default)
  Response:     { request_id, transcript, language_code }

★ Audio limits: sync REST accepts ≤30s clips. `VoiceMic` records short
  single-slot utterances (a name, a district, a village), so this is fine.
"""

import logging

import httpx

from app.config import settings

logger = logging.getLogger(__name__)


class VoiceEngineError(Exception):
    """Raised when the upstream Sarvam STT call fails in a non-recoverable way."""


class VoiceEngine:
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

        payload = resp.json()
        transcript = (payload.get("transcript") or "").strip()
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

        payload_resp = resp.json()
        audios = payload_resp.get("audios") or []
        audio_base64 = audios[0] if audios else None
        if not audio_base64:
            raise VoiceEngineError("Sarvam TTS returned an empty audio payload")

        return {
            "audio_base64": audio_base64,
            "audio_format": "wav",
            "request_id": payload_resp.get("request_id"),
        }


voice_engine = VoiceEngine()
