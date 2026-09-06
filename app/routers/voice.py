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

from fastapi import APIRouter, File, Form, HTTPException, UploadFile, Request

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
    request: Request,
    file: UploadFile | None = File(None),
    audio: UploadFile | None = File(None),
    locale: str = Form("mr"),
) -> TranscribeResponse:
    """Transcribe a short farmer utterance (name/district/village/phone) by
    proxying the uploaded clip to Sarvam STT.

    Accepts the audio under 'file', 'audio', any multipart file field, or raw binary body.
    """
    raw = None

    upload_filename = None

    # 1. Check declared multipart fields
    upload = file if file is not None else audio
    if upload is not None:
        raw = await upload.read()
        upload_filename = upload.filename

    # 2. Check any other file field in the multipart form (e.g. video, media, clip)
    if not raw:
        try:
            form = await request.form()
            for key, val in form.items():
                if isinstance(val, UploadFile):
                    data = await val.read()
                    if data:
                        raw = data
                        upload_filename = val.filename
                        break
                if key == "locale" and isinstance(val, str):
                    locale = val
        except Exception:
            pass

    # 3. Check if sent as raw binary body (Postman Body -> Binary)
    if not raw:
        body = await request.body()
        if body and len(body) > 100 and not body.startswith(b"------"):
            raw = body

    if not raw:
        raise HTTPException(
            status_code=422,
            detail="Missing audio file — please attach an audio/video file under key 'file' or 'audio'",
        )

    if len(raw) > 25 * 1024 * 1024:
        raise HTTPException(status_code=413, detail="Audio clip too large (max 25MB)")


    language_code = _LOCALE_TO_SARVAM.get(locale, "mr-IN")

    try:
        result = await voice_engine.speech_to_text(raw, filename=upload_filename, language_code=language_code)
    except VoiceEngineError as exc:
        raise HTTPException(status_code=502, detail=str(exc)) from exc

    return TranscribeResponse(**result)

