"""Mandi locations router — stub for Kartik to implement."""
from fastapi import APIRouter, Depends
from sqlalchemy.ext.asyncio import AsyncSession
from fastapi_cache.decorator import cache
from app.database import get_db

router = APIRouter()


# TODO: Kartik implements these endpoints
# GET /mandi-locations?district= — list seeded mandi locations
@router.get("/", response_model=list)
@cache(expire=3600)
async def get_mandi_locations(db: AsyncSession = Depends(get_db)):
    return []
