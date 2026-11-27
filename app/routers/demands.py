from typing import List, Optional
from fastapi import APIRouter, Depends, HTTPException, Query, status
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import or_, select

from app.database import get_db
from app.dependencies.auth import get_current_user, require_role
from app.models.user import User
from app.models.demand import BuyerDemand
from app.models.lot import Lot
from app.schemas.demand import DemandCreate, DemandOut
from app.schemas.matches import MatchesRes
from app.engines.matching_engine import (
    MatchingEngine,
    GreedyHaversineStrategy,
    FastClearanceStrategy,
    PriceOptimizedStrategy,
    matching_engine,
)
from app.utils.spatial import is_postgres, make_wkt_point, within_radius_filter

router = APIRouter()

@router.post("", response_model=DemandOut, status_code=status.HTTP_201_CREATED)
async def create_demand(
    payload: DemandCreate,
    user: User = Depends(require_role("BUYER")),
    db: AsyncSession = Depends(get_db)
):
    """Create a new buyer demand."""
    from app.utils.id_resolver import resolve_or_404
    commodity_db_id = (await resolve_or_404(db, "commodity", payload.commodity_id, "commodity_id")).id
    market_db_id = (await resolve_or_404(db, "market", payload.market_id, "market_id")).id if payload.market_id else None
    demand = BuyerDemand(
        buyer_id=user.id,
        commodity_id=commodity_db_id,
        quantity_qtl=payload.quantity_qtl,
        expected_price_paise=payload.expected_price_paise,
        market_id=market_db_id,
        warehouse_id=payload.warehouse_id,
        desired_grade=payload.desired_grade,
        lat=user.lat,
        lng=user.lng,
        geom=make_wkt_point(user.lat, user.lng) if is_postgres(db) else None,
        status="active"
    )
    db.add(demand)
    await db.commit()
    await db.refresh(demand)
    return DemandOut.model_validate(demand)

@router.get("", response_model=List[DemandOut])
async def list_demands(
    status_filter: Optional[str] = None,
    user: User = Depends(require_role("BUYER")),
    db: AsyncSession = Depends(get_db)
):
    """List demands owned by the current buyer."""
    query = select(BuyerDemand).where(BuyerDemand.buyer_id == user.id)
    if status_filter:
        query = query.where(BuyerDemand.status == status_filter)
    
    result = await db.execute(query)
    demands = result.scalars().all()
    return [DemandOut.model_validate(d) for d in demands]

@router.get("/{demand_id}/matches", response_model=MatchesRes)
async def get_demand_matches(
    demand_id: int,
    strategy: Optional[str] = Query("greedy", description="Matching strategy: greedy | fast_clearance | price_optimized"),
    user: User = Depends(require_role("BUYER")),
    db: AsyncSession = Depends(get_db)
):
    """Find matching lots for a demand using the selected Strategy Pattern algorithm."""
    result = await db.execute(select(BuyerDemand).where(BuyerDemand.id == demand_id))
    demand = result.scalar_one_or_none()
    
    if demand is None or demand.buyer_id != user.id:
        raise HTTPException(status_code=404, detail="Demand not found")

    # Instantiate strategy based on client request (GoF Strategy Pattern)
    if strategy == "fast_clearance":
        strat = FastClearanceStrategy()
    elif strategy == "price_optimized":
        strat = PriceOptimizedStrategy()
    else:
        strat = GreedyHaversineStrategy()

    lot_query = (
        select(Lot)
        .where(Lot.commodity_id == demand.commodity_id)
        .where(Lot.status.notin_(("sold", "cancelled")))
    )
    if is_postgres(db) and demand.lat is not None and demand.lng is not None:
        lot_query = lot_query.where(
            or_(
                Lot.geom.is_(None),
                within_radius_filter(Lot.geom, demand.lat, demand.lng, strat.max_radius_km),
            )
        )
    lot_result = await db.execute(lot_query)
    lots = lot_result.scalars().all()

    engine = MatchingEngine(strategy=strat)
    matches_dict = engine.match_lots_for_demand(lots, demand)
    return MatchesRes(**matches_dict)
