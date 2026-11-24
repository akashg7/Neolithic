from pydantic_settings import BaseSettings


class Settings(BaseSettings):
    DATABASE_URL: str = "postgresql+asyncpg://agrisense:agrisense@localhost:5432/agrisense"
    REDIS_URL: str = "redis://localhost:6379/1"
    CELERY_BROKER_URL: str = "redis://localhost:6379/0"
    JWT_SECRET: str = "change-me-in-production"
    JWT_ALGORITHM: str = "HS256"
    JWT_EXPIRE_MINUTES: int = 1440  # 24 hours
    # OTP policy (Member 1): 120 s TTL, 5 verify attempts, 3 issues / 10 min.
    OTP_TTL_SECONDS: int = 120
    OTP_MAX_ATTEMPTS: int = 5
    OTP_MAX_REQUESTS_PER_WINDOW: int = 3
    OTP_THROTTLE_WINDOW_SECONDS: int = 600
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
    # ── Demo / development switches (all ignored when ENV == "production") ──
    # A fixed OTP that every phone accepts — no SMS provider is wired yet.
    DEV_FIXED_OTP: str = ""
    # Enables POST /auth/demo-login (one-tap sign-in as the seeded demo farmer/buyer).
    DEMO_MODE: bool = False
    DEMO_FARMER_PHONE: str = "9822011111"
    DEMO_BUYER_PHONE: str = "9822022222"
    # Browser origins allowed to call the API directly (comma-separated). The web
    # build normally goes through a same-origin proxy and needs none of these.
    CORS_ORIGINS: str = "http://localhost:8080,http://127.0.0.1:8080"

    # ── Agent / NLP (Track C reads these; all optional — the API boots without them) ──
    LLM_PROVIDER: str = "gemini"            # gemini | openai | groq
    GEMINI_API_KEY: str = ""
    GEMINI_MODEL: str = "gemini-2.5-flash"
    OPENAI_API_KEY: str = ""
    QDRANT_URL: str = "http://localhost:6333"
    QDRANT_API_KEY: str = ""
    QDRANT_COLLECTION: str = "krishi_mitr_kb"
    EMBEDDING_MODEL: str = "BAAI/bge-m3"
    AGENT_MEMORY_REDIS_URL: str = "redis://localhost:6379/2"   # 0=Celery, 1=HTTP cache, 2=agent memory

    @property
    def is_production(self) -> bool:
        return self.ENV.lower() == "production"


    class Config:
        env_file = ".env"
        extra = "ignore"



settings = Settings()
