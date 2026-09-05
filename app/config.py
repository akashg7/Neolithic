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

    class Config:
        env_file = ".env"


settings = Settings()
