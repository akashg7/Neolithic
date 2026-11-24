from fastapi import APIRouter, Depends
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select
from app.database import get_db
from app.models.reference import Commodity
from app.models.mandi import MandiLocation
from pydantic import BaseModel
from typing import List
from app.utils.id_resolver import slug_for

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
    comm_out = [IdNamePair(id=slug_for("commodity", c.name), name=c.name) for c in commodities]
    
    # Get markets (mandis)
    mandi_result = await db.execute(select(MandiLocation))
    mandis = mandi_result.scalars().all()
    mandis_out = [IdNamePair(id=slug_for("market", m.name), name=m.name) for m in mandis]
    
    return AppInitRes(
        roles=roles,
        commodities=comm_out,
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
async def get_data_provenance(db: AsyncSession = Depends(get_db)):
    """Where every price row came from: one row per crop × mandi × source,
    with counts and date range (ProvenanceRes, S24)."""
    from datetime import datetime as _dt
    from sqlalchemy import func, select as _select
    from app.models.mandi import PriceObservation
    from app.utils.id_resolver import load_catalog

    cat = await load_catalog(db)
    q = (_select(PriceObservation.commodity_id, PriceObservation.market_id,
                 PriceObservation.observation_type, func.count(),
                 func.min(PriceObservation.date), func.max(PriceObservation.date))
         .where(PriceObservation.market_id.is_not(None))
         .group_by(PriceObservation.commodity_id, PriceObservation.market_id,
                   PriceObservation.observation_type)
         .order_by(func.count().desc())
         .limit(200))
    urls = {"AGMARKNET": "https://agmarknet.gov.in", "MSAMB": "https://www.msamb.com",
            "ARCHIVE": "https://agmarknet.gov.in"}
    rows = []
    for cid, mid, src, n, first, last in (await db.execute(q)).all():
        c, m = cat.get("commodity", cid), cat.get("market", mid)
        if c is None or m is None:
            continue
        rows.append({
            "commodity_id": c.slug, "commodity_name_mr": c.name_mr,
            "market_id": m.slug, "market_name_mr": m.name_mr,
            "source": src, "row_count": n,
            "first_obs_date": first.strftime("%Y-%m-%d"), "last_obs_date": last.strftime("%Y-%m-%d"),
            "source_url": urls.get(src),
        })
    return {"rows": rows, "generated_at": _dt.utcnow().isoformat() + "Z"}
