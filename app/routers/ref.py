from fastapi import APIRouter, Depends
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select
from typing import List

from app.database import get_db
from app.models.reference import District, Commodity, Warehouse
from app.models.mandi import MandiLocation
from app.schemas.ref import DistrictOut, CommodityOut, WarehouseOut, MandiOut

router = APIRouter()

@router.get("/districts", response_model=List[DistrictOut])
async def get_districts(db: AsyncSession = Depends(get_db)):
    """Get all districts."""
    result = await db.execute(select(District).order_by(District.name))
    return result.scalars().all()

@router.get("/commodities", response_model=List[CommodityOut])
async def get_commodities(db: AsyncSession = Depends(get_db)):
    """Get all commodities."""
    result = await db.execute(select(Commodity).order_by(Commodity.name))
    return result.scalars().all()

@router.get("/warehouses", response_model=List[WarehouseOut])
async def get_warehouses(db: AsyncSession = Depends(get_db)):
    """Get all warehouses."""
    result = await db.execute(select(Warehouse).order_by(Warehouse.name))
    return result.scalars().all()

@router.get("/markets", response_model=List[MandiOut])
async def get_markets(db: AsyncSession = Depends(get_db)):
    """Get all mandi locations (markets)."""
    result = await db.execute(select(MandiLocation).order_by(MandiLocation.name))
    return result.scalars().all()
