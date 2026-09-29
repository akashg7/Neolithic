from pydantic_settings import BaseSettings


class Settings(BaseSettings):
    DATABASE_URL: str = "postgresql+asyncpg://agrisense:agrisense@localhost:5432/agrisense"
    REDIS_URL: str = "redis://localhost:6379/1"
    CELERY_BROKER_URL: str = "redis://localhost:6379/0"
    JWT_SECRET: str = "change-me-in-production"
    JWT_ALGORITHM: str = "HS256"
    JWT_EXPIRE_MINUTES: int = 1440  # 24 hours
    RAZORPAY_KEY_ID: str = ""
    RAZORPAY_KEY_SECRET: str = ""
    S3_ENDPOINT: str = "http://localhost:9000"
    S3_ACCESS_KEY: str = "minioadmin"
    S3_SECRET_KEY: str = "minioadmin"
    S3_BUCKET: str = "agrisense"
    BHASHINI_API_KEY: str = ""       # Tier 3
    BHASHINI_USER_ID: str = ""       # Tier 3
    AGORA_APP_ID: str = ""           # Tier 3
    AGORA_APP_CERTIFICATE: str = ""  # Tier 3
    # Sarvam AI — speech-to-text (STT). The mobile app (`VoiceMic`) records a
    # clip and POSTs it to our /voice/transcribe; this backend proxies the
    # audio to Sarvam and returns the transcript. Model default mirrors the
    # app's own `app/src/voice/config.ts` (`sarvamAsrModel: 'saaras:v3'`).
    SARVAM_API_KEY: str = ""
    SARVAM_ASR_ENDPOINT: str = "https://api.sarvam.ai/speech-to-text"
    SARVAM_ASR_MODEL: str = "saaras:v3"
    # Sarvam AI — text-to-speech (TTS). Same keys the frontend voice module
    # reads (`app/src/voice/config.ts`), kept server-side for later /narrate.
    SARVAM_TTS_ENDPOINT: str = "https://api.sarvam.ai/text-to-speech"
    SARVAM_NORMALIZE_ENDPOINT: str = "https://api.sarvam.ai/v1/chat/completions"
    SARVAM_TTS_SPEAKER: str = "shubh"
    # Voice behaviour knobs (mirror app/src/voice/config.ts). Used to bound
    # clip length and gate low-confidence transcripts before they reach the
    # RegistrationAgent.
    VOICE_CONFIDENCE_THRESHOLD: float = 0.6
    VOICE_MAX_RECORDING_SECONDS: int = 10
    VOICE_CACHE_ENABLED: bool = True
    ENV: str = "development"


    class Config:
        env_file = ".env"
        extra = "ignore"



settings = Settings()
