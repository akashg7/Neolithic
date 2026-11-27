"""Logistics router — transport and storage provider discovery."""
from typing import Optional, List, Dict, Any
from fastapi import APIRouter, Depends, Query
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select

from app.database import get_db
from app.models.logistics import LogisticsProvider
from app.schemas.logistics import (
    LogisticsProviderOut,
    TransportEstimateReq,
    TransportEstimateOut,
)
from app.utils.haversine import haversine_km
from app.utils.spatial import distance_km_expr, is_postgres, within_radius_filter

router = APIRouter()


@router.get("", response_model=List[LogisticsProviderOut])
@router.get("/", response_model=List[LogisticsProviderOut])
async def list_logistics_providers(
    type: Optional[str] = None,
    lat: Optional[float] = None,
    lng: Optional[float] = None,
    radius_km: Optional[float] = None,
    db: AsyncSession = Depends(get_db)
):
    """List logistics providers with optional type and PostGIS geo-filtering."""
    if lat is not None and lng is not None and is_postgres(db):
        dist_col = distance_km_expr(LogisticsProvider.geom, lat, lng).label("distance_km")
        query = select(LogisticsProvider, dist_col).where(LogisticsProvider.geom.is_not(None))
        if type:
            query = query.where(LogisticsProvider.type == type)
        if radius_km is not None:
            query = query.where(within_radius_filter(LogisticsProvider.geom, lat, lng, radius_km))
        query = query.order_by(dist_col.asc())
        rows = (await db.execute(query)).all()
        return [
            LogisticsProviderOut(
                id=p.id,
                name=p.name,
                type=p.type,
                lat=p.lat,
                lng=p.lng,
                distance_km=round(float(dist_km), 2) if dist_km is not None else None,
                capacity_kg=p.capacity_kg,
                contact=p.contact,
                source=p.source or "demo",
            )
            for p, dist_km in rows
        ]

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
    """Retrieve nearby storage facilities and transport operators using PostGIS ST_DWithin."""
    storage = []
    transport = []

    if is_postgres(db):
        dist_col = distance_km_expr(LogisticsProvider.geom, lat, lng).label("distance_km")
        query = (
            select(LogisticsProvider, dist_col)
            .where(within_radius_filter(LogisticsProvider.geom, lat, lng, radius_km))
            .order_by(dist_col.asc())
        )
        rows = (await db.execute(query)).all()
        for p, dist_km in rows:
            item = {
                "id": p.id,
                "name": p.name,
                "type": p.type,
                "lat": p.lat,
                "lng": p.lng,
                "distance_km": round(float(dist_km), 2),
                "capacity_kg": p.capacity_kg,
                "contact": p.contact,
                "source": p.source or "demo",
            }
            if p.type == "storage":
                storage.append(item)
            else:
                transport.append(item)
        return {
            "storage": storage,
            "transport": transport,
            "total": len(storage) + len(transport),
        }

    result = await db.execute(select(LogisticsProvider))
    providers = result.scalars().all()

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


@router.post("/estimate", response_model=TransportEstimateOut)
async def estimate_transport_cost(req: TransportEstimateReq) -> TransportEstimateOut:
    """
    Estimate freight transit costs and duration based on Haversine distance and volume.
    Member 3: Akash — Spatial Routing & Logistics.
    """
    dist_km = round(haversine_km(req.origin_lat, req.origin_lng, req.dest_lat, req.dest_lng), 2)
    
    # Base rate: 450 paise (₹4.50) per km + capacity scaling
    base_rate_km_paise = 450
    # Freight formula: Base transit + 35 paise per quintal-km
    total_freight_paise = int((dist_km * base_rate_km_paise) + (dist_km * req.qty_qtl * 35))
    
    # Average rural cargo transit speed ~45 km/h + 1 hr loading/unloading buffer
    transit_hours = round(max(1.0, (dist_km / 45.0) + 1.0), 1)

    return TransportEstimateOut(
        distance_km=dist_km,
        qty_qtl=req.qty_qtl,
        base_rate_per_km_paise=base_rate_km_paise,
        estimated_freight_paise=total_freight_paise,
        estimated_transit_hours=transit_hours,
        route_summary=f"{dist_km} km freight transit for {req.qty_qtl} qtl {req.commodity_name or 'produce'}"
    )

