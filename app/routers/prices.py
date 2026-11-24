from typing import Optional
from fastapi import APIRouter, Depends, Query
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select
from datetime import datetime, timedelta

from app.database import get_db
from app.models.mandi import PriceObservation, MandiLocation
from app.schemas.prices import PriceSeriesRes, NearbyRes, PricePoint, NearbyMarketRow
from app.services import price_service
from app.utils.id_resolver import resolve_or_404
from app.dependencies.auth import get_optional_user
from app.models.user import User

router = APIRouter()

@router.get("/series", response_model=PriceSeriesRes)
async def get_price_series(
    commodity_id: str,
    market_id: str,
    days: int = Query(180, ge=1, le=365),
    db: AsyncSession = Depends(get_db)
):
    """Get price series for a commodity and market. Accepts slug or integer IDs."""
    commodity = await resolve_or_404(db, "commodity", commodity_id, "commodity_id")
    market = await resolve_or_404(db, "market", market_id, "market_id")
    series = await price_service.price_series(db, commodity.id, market.id, days)
    return PriceSeriesRes(
        points=[PricePoint(**p) for p in series["points"]],
        source_summary=series["source_summary"],
        latest_obs_date=series["latest_obs_date"],
    )

@router.get("/nearby", response_model=NearbyRes)
async def get_nearby_markets(
    commodity_id: str,
    district_id: Optional[str] = None,
    lat: Optional[float] = None,
    lng: Optional[float] = None,
    radius_km: float = Query(250, ge=10, le=600),
    db: AsyncSession = Depends(get_db),
    user: Optional[User] = Depends(get_optional_user),
):
    """Mandis with a recent price for this crop, ranked by net ₹/qtl after
    transport, commission and loading. Origin: lat/lng → the caller's profile
    location → the district's mandi centroid."""
    commodity = await resolve_or_404(db, "commodity", commodity_id, "commodity_id")
    district = await resolve_or_404(db, "district", district_id, "district_id") if district_id else None
    district_db_id = district.id if district else (user.district_id if user else None)

    origin = None
    if lat is not None and lng is not None:
        origin = (lat, lng)
    elif user is not None and user.lat is not None and user.lng is not None:
        origin = (user.lat, user.lng)
    elif district_db_id is not None:
        origin = await price_service.district_centroid(db, district_db_id)

    res = await price_service.nearby_markets(db, commodity.id, origin=origin,
                                             from_district_id=district_db_id, radius_km=radius_km)
    return NearbyRes(as_of_date=res["as_of_date"],
                     rows=[NearbyMarketRow(**r) for r in res["rows"]],
                     sorted_by="net_paise_per_qtl")
