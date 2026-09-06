from typing import Optional
from fastapi import APIRouter, Depends, Query
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select
from datetime import datetime, timedelta

from app.database import get_db
from app.models.mandi import PriceObservation, MandiLocation
from app.schemas.prices import PriceSeriesRes, NearbyRes, PricePoint, NearbyMarketRow

router = APIRouter()

@router.get("/series", response_model=PriceSeriesRes)
async def get_price_series(
    commodity_id: int,
    market_id: int,
    days: int = Query(180, ge=1, le=365),
    db: AsyncSession = Depends(get_db)
):
    """Get price series for a commodity and market."""
    start_date = datetime.utcnow() - timedelta(days=days)
    
    query = (
        select(PriceObservation)
        .where(PriceObservation.commodity_id == commodity_id)
        .where(PriceObservation.market_id == market_id)
        .where(PriceObservation.date >= start_date)
        .order_by(PriceObservation.date.asc())
    )
    result = await db.execute(query)
    observations = result.scalars().all()
    
    points = []
    source_summary = {}
    latest_date = None
    
    for obs in observations:
        obs_date_str = obs.date.strftime("%Y-%m-%d")
        source = obs.observation_type if obs.observation_type in ['AGMARKNET', 'MSAMB', 'ARCHIVE', 'IMPUTED', 'SYNTHETIC'] else 'IMPUTED'
        
        points.append(PricePoint(
            obs_date=obs_date_str,
            min_paise_per_qtl=obs.min_price_paise or obs.modal_price_paise,
            max_paise_per_qtl=obs.max_price_paise or obs.modal_price_paise,
            modal_paise_per_qtl=obs.modal_price_paise,
            arrivals_qtl=obs.arrivals_qtl or 0,
            source=source
        ))
        
        source_summary[source] = source_summary.get(source, 0) + 1
        
        if latest_date is None or obs_date_str > latest_date:
            latest_date = obs_date_str
            
    if not latest_date:
        latest_date = datetime.utcnow().strftime("%Y-%m-%d")
        
    return PriceSeriesRes(
        points=points,
        source_summary=source_summary,
        latest_obs_date=latest_date
    )

@router.get("/nearby", response_model=NearbyRes)
async def get_nearby_markets(
    commodity_id: int,
    district_id: int,
    db: AsyncSession = Depends(get_db)
):
    """Get nearby markets sorted by net profit."""
    # Stub implementation: fetch markets in the same district and return mock price rows
    query = select(MandiLocation).where(MandiLocation.district_id == district_id)
    result = await db.execute(query)
    markets = result.scalars().all()
    
    rows = []
    for m in markets:
        # Mock calculation
        gross = 250000
        transport = 15000
        commission = 5000
        net = gross - transport - commission
        
        rows.append(NearbyMarketRow(
            market_id=str(m.id),
            name_mr=m.name_mr,
            gross_paise_per_qtl=gross,
            transport_paise_per_qtl=transport,
            commission_paise_per_qtl=commission,
            net_paise_per_qtl=net,
            distance_km=45,
            source='IMPUTED'
        ))
        
    # Must sort by net_paise_per_qtl descending
    rows.sort(key=lambda r: r.net_paise_per_qtl, reverse=True)
    
    return NearbyRes(
        as_of_date=datetime.utcnow().strftime("%Y-%m-%d"),
        rows=rows,
        sorted_by="net_paise_per_qtl"
    )
