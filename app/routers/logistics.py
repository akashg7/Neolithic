"""Logistics router — transport and storage provider discovery."""
import math
from typing import Optional, List, Dict, Any
from fastapi import APIRouter, Depends, Query
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select

from app.database import get_db
from app.models.logistics import LogisticsProvider
from app.schemas.logistics import LogisticsProviderOut

router = APIRouter()


def haversine_km(lat1: float, lon1: float, lat2: float, lon2: float) -> float:
    r = 6371.0
    dlat = math.radians(lat2 - lat1)
    dlon = math.radians(lon2 - lon1)
    a = math.sin(dlat / 2) ** 2 + math.cos(math.radians(lat1)) * math.cos(math.radians(lat2)) * math.sin(dlon / 2) ** 2
    c = 2 * math.atan2(math.sqrt(a), math.sqrt(1 - a))
    return r * c


@router.get("", response_model=List[LogisticsProviderOut])
@router.get("/", response_model=List[LogisticsProviderOut])
async def list_logistics_providers(
    type: Optional[str] = None,
    lat: Optional[float] = None,
    lng: Optional[float] = None,
    radius_km: Optional[float] = None,
    db: AsyncSession = Depends(get_db)
):
    """List logistics providers with optional type and geo-filtering."""
    query = select(LogisticsProvider)
    if type:
        query = query.where(LogisticsProvider.type == type)
    result = await db.execute(query)
    providers = result.scalars().all()

    out = []
    for p in providers:
        dist = None
        if lat is not None and lng is not None:
            dist = round(haversine_km(lat, lng, p.lat, p.lng), 2)
            if radius_km is not None and dist > radius_km:
                continue
        out.append(LogisticsProviderOut(
            id=p.id,
            name=p.name,
            type=p.type,
            lat=p.lat,
            lng=p.lng,
            distance_km=dist,
            capacity_kg=p.capacity_kg,
            contact=p.contact,
            source=p.source or "demo"
        ))

    if lat is not None and lng is not None:
        out.sort(key=lambda x: (x.distance_km if x.distance_km is not None else float('inf')))
    return out


@router.get("/nearby")
async def get_nearby_logistics(
    lat: float = Query(..., description="Latitude"),
    lng: float = Query(..., description="Longitude"),
    radius_km: float = Query(50.0, description="Radius in kilometers"),
    db: AsyncSession = Depends(get_db)
) -> Dict[str, Any]:
    """Retrieve nearby storage facilities and transport operators partitioned by type."""
    result = await db.execute(select(LogisticsProvider))
    providers = result.scalars().all()

    storage = []
    transport = []

    for p in providers:
        dist = round(haversine_km(lat, lng, p.lat, p.lng), 2)
        if dist <= radius_km:
            item = {
                "id": p.id,
                "name": p.name,
                "type": p.type,
                "lat": p.lat,
                "lng": p.lng,
                "distance_km": dist,
                "capacity_kg": p.capacity_kg,
                "contact": p.contact,
                "source": p.source or "demo"
            }
            if p.type == "storage":
                storage.append(item)
            else:
                transport.append(item)

    storage.sort(key=lambda x: x["distance_km"])
    transport.sort(key=lambda x: x["distance_km"])

    return {
        "storage": storage,
        "transport": transport,
        "total": len(storage) + len(transport)
    }

