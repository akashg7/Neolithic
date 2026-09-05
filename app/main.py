from contextlib import asynccontextmanager
from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from fastapi_cache import FastAPICache
from fastapi_cache.backends.redis import RedisBackend
from redis import asyncio as aioredis

from app.config import settings
from app.engines.price_engine import price_engine
from app.middleware.error_handler import ErrorHandlerMiddleware
from app.routers import (
    auth, users, lots, demands, offers,
    transactions, logistics, disputes, fpo, mandi, ai, voice
)


@asynccontextmanager
async def lifespan(app: FastAPI):
    # Initialize Redis caching
    redis = aioredis.from_url(settings.REDIS_URL)
    FastAPICache.init(RedisBackend(redis), prefix="agrisense-cache")
    
    # Startup: load AI models into memory
    try:
        price_engine.load_models()
    except Exception:
        pass  # Models may not be available yet — that's OK
    yield
    # Shutdown: cleanup


app = FastAPI(
    title="AgriSense API",
    version="1.0.0",
    description="Backend API for AgriSense — SIH PS 26132",
    lifespan=lifespan,
)

# Middleware
app.add_middleware(ErrorHandlerMiddleware)
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],  # Lock down in production
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Register routers
app.include_router(auth.router, prefix="/auth", tags=["Auth"])
app.include_router(users.router, prefix="/users", tags=["Users"])
app.include_router(lots.router, prefix="/lots", tags=["Lots"])
app.include_router(demands.router, prefix="/demands", tags=["Demands"])
app.include_router(offers.router, prefix="/offers", tags=["Offers"])
app.include_router(transactions.router, prefix="/transactions", tags=["Transactions"])
app.include_router(logistics.router, prefix="/logistics", tags=["Logistics"])
app.include_router(disputes.router, prefix="/disputes", tags=["Disputes"])
app.include_router(fpo.router, prefix="/fpo", tags=["FPO"])
app.include_router(mandi.router, prefix="/mandi-locations", tags=["Mandi"])
app.include_router(ai.router, prefix="/ai", tags=["AI"])
app.include_router(voice.router, prefix="/voice", tags=["Voice"])


@app.get("/health", tags=["Health"])
async def health():
    return {"status": "ok"}
