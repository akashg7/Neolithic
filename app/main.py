from contextlib import asynccontextmanager
from fastapi import FastAPI, Request
from fastapi.middleware.cors import CORSMiddleware
from fastapi.exceptions import RequestValidationError
from fastapi.responses import JSONResponse
from starlette.exceptions import HTTPException as StarletteHTTPException
from fastapi_cache import FastAPICache
from fastapi_cache.backends.redis import RedisBackend
from redis import asyncio as aioredis

from app.config import settings
from app.engines.price_engine import price_engine
from app.middleware.error_handler import ErrorHandlerMiddleware
from app.routers import (
    auth, lots, demands, offers,
    transactions, logistics, disputes, fpo, ai, voice,
    ref, prices, meta, buyers
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

# Exception handlers
@app.exception_handler(RequestValidationError)
async def validation_exception_handler(request: Request, exc: RequestValidationError):
    field = exc.errors()[0]["loc"][-1] if exc.errors() else None
    return JSONResponse(
        status_code=400,
        content={
            "error": {
                "code": "VALIDATION_FAILED",
                "message": "Validation error",
                "field": field
            }
        },
    )

@app.exception_handler(StarletteHTTPException)
async def http_exception_handler(request: Request, exc: StarletteHTTPException):
    code_map = {
        400: "VALIDATION_FAILED",
        401: "UNAUTHENTICATED",
        403: "FORBIDDEN",
        404: "NOT_FOUND",
        409: "CONFLICT",
        422: "INSUFFICIENT_DATA",
        429: "RATE_LIMITED",
    }
    code = code_map.get(exc.status_code, "API_ERROR")
    return JSONResponse(
        status_code=exc.status_code,
        content={
            "error": {
                "code": code,
                "message": exc.detail,
                "field": None
            }
        },
    )

# Register routers with /api/v1 prefix
app.include_router(auth.router, prefix="/api/v1/auth", tags=["Auth"])
app.include_router(lots.router, prefix="/api/v1/lots", tags=["Lots"])
app.include_router(demands.router, prefix="/api/v1/demands", tags=["Demands"])
app.include_router(offers.router, prefix="/api/v1/offers", tags=["Offers"])
app.include_router(transactions.router, prefix="/api/v1/tx", tags=["Transactions"])
app.include_router(logistics.router, prefix="/api/v1/logistics", tags=["Logistics"])
app.include_router(disputes.router, prefix="/api/v1/disputes", tags=["Disputes"])
app.include_router(fpo.router, prefix="/api/v1/pools", tags=["FPO"])
app.include_router(ai.router, prefix="/api/v1/ai", tags=["AI"])
app.include_router(voice.router, prefix="/api/v1/voice", tags=["Voice"])
app.include_router(ref.router, prefix="/api/v1/ref", tags=["Reference"])
app.include_router(prices.router, prefix="/api/v1/prices", tags=["Prices"])
app.include_router(meta.router, prefix="/api/v1/meta", tags=["Meta"])
app.include_router(buyers.router, prefix="/api/v1/buyers", tags=["Buyers"])


@app.get("/health", tags=["Health"])
async def health():
    return {"status": "ok"}
