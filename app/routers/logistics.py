"""Logistics router — stub for Kartik to implement."""
from fastapi import APIRouter, Depends
from fastapi_cache.decorator import cache
from sqlalchemy.ext.asyncio import AsyncSession
from app.database import get_db

router = APIRouter()


# TODO: Kartik implements these endpoints
# GET /logistics?lat=&lng=&type=&radius_km= — nearby providers

@router.get("/", response_model=list[LogisticsProviderOut])
@cache(expire=3600)
async def list_logistics_providers(type: str = None, db: AsyncSession = Depends(get_db)):
    pass
