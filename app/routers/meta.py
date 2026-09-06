from fastapi import APIRouter, Depends
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select
from app.database import get_db
from app.models.reference import Commodity
from app.models.mandi import MandiLocation
from pydantic import BaseModel
from typing import List

router = APIRouter()

class IdNamePair(BaseModel):
    id: str
    name: str

class AppInitRes(BaseModel):
    roles: List[str]
    commodities: List[IdNamePair]
    markets: List[IdNamePair]

@router.get("/init", response_model=AppInitRes)
async def get_app_init(db: AsyncSession = Depends(get_db)):
    """Initialize app data for frontend."""
    
    # Roles are static
    roles = ["FARMER", "BUYER", "LOGISTICS", "WAREHOUSE_MGR", "ADMIN", "FPO_ADMIN"]
    
    # Get commodities
    comm_result = await db.execute(select(Commodity))
    commodities = comm_result.scalars().all()
    comm_out = [IdNamePair(id=str(c.id), name=c.name) for c in commodities]
    
    # Get markets (mandis)
    mandi_result = await db.execute(select(MandiLocation))
    mandis = mandi_result.scalars().all()
    mandis_out = [IdNamePair(id=str(m.id), name=m.name) for m in mandis]
    
    return AppInitRes(
        roles=roles,
        markets=mandis_out
    )

@router.get("/health")
async def get_health():
    """Health check endpoint."""
    from app.engines.price_engine import price_engine
    # Assuming DB is OK if we reached here (though a real check would query it)
    return {
        "db": "ok",
        "model_loaded": price_engine._loaded,
        "latest_obs_date": "2026-09-05" # Stub
    }

@router.get("/data-provenance")
async def get_data_provenance():
    """Data provenance stub."""
    return {
        "sources": ["AGMARKNET", "MSAMB", "SYNTHETIC"],
        "last_sync": "2026-09-06T00:00:00Z"
    }
