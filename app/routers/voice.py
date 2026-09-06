"""Voice router — Sarvam-backed speech proxy for the mobile app.

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

`POST /voice/narrate` accepts `{text, locale}` and returns Sarvam-synthesized
Marathi audio as base64 WAV — the sale-window voice agent's TTS path. The audio
for a dynamic sentence (a farmer's lot, dates, amounts) can't be a pre-recorded
clip, so it is synthesized on demand. The Sarvam key stays server-side; the app
only ever talks to us. On-device TTS (`speakText`) remains the offline fallback
on the device when this route is unreachable.
"""

from fastapi import APIRouter, File, Form, HTTPException, UploadFile, Request

from app.engines.voice_engine import VoiceEngineError, voice_engine
from app.schemas.voice import NarrateRequest, NarrateResponse, TranscribeResponse

router = APIRouter()

# Locale → Sarvam BCP-47 language code. The app's default is Marathi; the two
# other locales the app ships map to their Sarvam codes too.
_LOCALE_TO_SARVAM: dict[str, str] = {
    "mr": "mr-IN",
    "hi": "hi-IN",
    "en": "en-IN",
}


@router.post("/narrate", response_model=NarrateResponse)
async def narrate(payload: NarrateRequest) -> NarrateResponse:
    """Synthesize Marathi speech for `text` via Sarvam TTS (bulbul:v3) and
    return it as base64 WAV. This is the sale-window voice agent's live spoke
    audio path — the narration sentence is dynamic and can't be pre-recorded.
    """
    if not voice_engine.configured:
        raise HTTPException(status_code=503, detail="Voice narration is not configured (SARVAM_API_KEY)")

    language_code = _LOCALE_TO_SARVAM.get(payload.locale, "mr-IN")
    try:
        result = await voice_engine.text_to_speech(payload.text, language_code=language_code)
    except VoiceEngineError as exc:
        raise HTTPException(status_code=502, detail=str(exc)) from exc

    return NarrateResponse(**result)


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

