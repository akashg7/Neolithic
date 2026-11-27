from fastapi import APIRouter, Depends
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select
from typing import List, Optional

from app.database import get_db
from app.models.reference import District, Commodity, Warehouse
from app.models.mandi import MandiLocation
from app.schemas.ref import DistrictOut, CommodityOut, WarehouseOut, MandiOut
from app.utils.cache import safe_cache
from app.utils.id_resolver import load_catalog, resolve_or_404

router = APIRouter()


@router.get("/districts", response_model=List[DistrictOut])
@safe_cache(expire=3600, namespace="ref")
async def get_districts(db: AsyncSession = Depends(get_db)):
    """All districts. `id` is the app slug (e.g. `dist_nashik`)."""
    await load_catalog(db)
    result = await db.execute(select(District).order_by(District.name))
    return [DistrictOut.model_validate(r) for r in result.scalars().all()]


@router.get("/commodities", response_model=List[CommodityOut])
@safe_cache(expire=3600, namespace="ref")
async def get_commodities(db: AsyncSession = Depends(get_db)):
    """All commodities. `id` is the app slug (e.g. `cmd_onion`)."""
    result = await db.execute(select(Commodity).order_by(Commodity.name))
    return [CommodityOut.model_validate(r) for r in result.scalars().all()]


@router.get("/warehouses", response_model=List[WarehouseOut])
@safe_cache(expire=3600, namespace="ref")
async def get_warehouses(district_id: Optional[str] = None, db: AsyncSession = Depends(get_db)):
    """Warehouses, optionally for one district (slug or id)."""
    await load_catalog(db)
    q = select(Warehouse).order_by(Warehouse.name)
    if district_id:
        q = q.where(Warehouse.district_id == (await resolve_or_404(db, "district", district_id, "district_id")).id)
    result = await db.execute(q)
    return [WarehouseOut.model_validate(r) for r in result.scalars().all()]


@router.get("/mandis", response_model=List[MandiOut])
@router.get("/markets", response_model=List[MandiOut])
@safe_cache(expire=3600, namespace="ref")
async def get_markets(district_id: Optional[str] = None, db: AsyncSession = Depends(get_db)):
    """Mandis, optionally for one district (slug or id). `id` is the app slug."""
    await load_catalog(db)
    q = select(MandiLocation).order_by(MandiLocation.name)
    if district_id:
        q = q.where(MandiLocation.district_id == (await resolve_or_404(db, "district", district_id, "district_id")).id)
    result = await db.execute(q)
    return [MandiOut.model_validate(r) for r in result.scalars().all()]
