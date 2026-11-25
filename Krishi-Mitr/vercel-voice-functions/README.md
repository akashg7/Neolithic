# Vercel voice functions (disabled)

These used to live in `api/v1/voice/`. Vercel serves files under `api/` as
serverless functions *ahead of* the `/api/v1/*` rewrite in `vercel.json`, so
voice requests on the website went here instead of the backend, and failed
whenever `SARVAM_API_KEYS` wasn't set on the Vercel project.

Voice now goes through the backend like every other call
(`/api/v1/voice/narrate`, `/api/v1/voice/transcribe` → FastAPI → Sarvam), using
the key in the server's `.env`. To use these functions again, move them back
to `api/v1/voice/` and set `SARVAM_API_KEYS` in Vercel.
