"""Voice router — Sarvam-backed speech-to-text proxy for the mobile app.

`POST /voice/transcribe` accepts a short audio clip (multipart `file` OR
`audio` field — see `transcribe()`), plus an optional `locale` form field
matching the frontend's `mr`/`hi`/`en`. It proxies the clip to Sarvam and
returns `{transcript}` — the exact shape `frontend/src/lib/api.ts`'s
`transcribeAudio()` already expects.

★ Deliberately unauthenticated, like the `/ai/*` endpoints. The mic on S2/S3
  runs *during registration*, before the farmer holds a JWT (`signIn` happens
  only after `register` succeeds), and the frontend's `transcribeAudio()`
  attaches a Bearer token only when one exists. Requiring `get_current_user`
  here would break the exact registration path this endpoint exists to serve.
  Abuse control belongs to a rate limiter (per-IP), not a per-user token this
  flow cannot have yet.

TTS (`/voice/narrate`) is intentionally not wired: the frontend speaks dynamic
text via on-device TTS (`speakText`) and static phrases via pre-generated
clips, so a server round trip buys nothing today.
"""

from fastapi import APIRouter, File, Form, HTTPException, UploadFile
from app.engines.voice_engine import VoiceEngineError, voice_engine
from app.schemas.voice import TranscribeResponse

router = APIRouter()

# Locale → Sarvam BCP-47 language code. The app's default is Marathi; the two
# other locales the app ships map to their Sarvam codes too.
_LOCALE_TO_SARVAM: dict[str, str] = {
    "mr": "mr-IN",
    "hi": "hi-IN",
    "en": "en-IN",
}


@router.post("/transcribe", response_model=TranscribeResponse)
async def transcribe(
    file: UploadFile | None = File(None),
    audio: UploadFile | None = File(None),
    locale: str = Form("mr"),
) -> TranscribeResponse:
    """Transcribe a short farmer utterance (name/district/village/phone) by
    proxying the uploaded clip to Sarvam STT.

    Accepts the audio under EITHER multipart field name: `file` (the Sarvam/
    OpenAPI convention) or `audio` (what `frontend/src/lib/api.ts`'s
    `transcribeAudio()` actually sends). The two were written independently
    and disagreed; accepting both keeps each side honest without a coordinated
    release.
    """
    upload = file if file is not None else audio
    if upload is None:
        raise HTTPException(
            status_code=422,
            detail="Missing audio file — send it as multipart field 'file' or 'audio'",
        )

    if not voice_engine.configured:
        raise HTTPException(status_code=503, detail="Voice transcription is not configured (SARVAM_API_KEY)")

    raw = await upload.read()
    if not raw:
        raise HTTPException(status_code=400, detail="Empty audio file")

    # Coarse upload guard. The client's `VoiceMic` records ≤10s AAC (~80–160KB);
    # Sarvam's sync REST caps at 30s. 2MB is far above any legitimate clip but
    # stops a runaway/abusive upload before it costs an upstream call.
    if len(raw) > 2 * 1024 * 1024:
        raise HTTPException(status_code=413, detail="Audio clip too large (max 2MB)")

    # The app's sync-REST clip is a single short slot utterance — well under
    # Sarvam's 30s cap — so no length check is needed beyond the byte guard.
    language_code = _LOCALE_TO_SARVAM.get(locale, "mr-IN")

    try:
        result = await voice_engine.speech_to_text(raw, language_code=language_code)
    except VoiceEngineError as exc:
        raise HTTPException(status_code=502, detail=str(exc)) from exc

    return TranscribeResponse(**result)
