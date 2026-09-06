from typing import List, Optional
from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select

from app.database import get_db
from app.dependencies.auth import get_current_user, require_role
from app.models.user import User
from app.models.demand import BuyerDemand
from app.models.lot import Lot
from app.schemas.demand import DemandCreate, DemandOut
from app.schemas.matches import MatchesRes
from app.engines import matching_engine

router = APIRouter()

@router.post("", response_model=DemandOut, status_code=status.HTTP_201_CREATED)
async def create_demand(
    payload: DemandCreate,
    user: User = Depends(require_role("BUYER")),
    db: AsyncSession = Depends(get_db)
):
    """Create a new buyer demand."""
    demand = BuyerDemand(
        buyer_id=user.id,
        commodity_id=payload.commodity_id,
        quantity_qtl=payload.quantity_qtl,
        expected_price_paise=payload.expected_price_paise,
        market_id=payload.market_id,
        warehouse_id=payload.warehouse_id,
        desired_grade=payload.desired_grade,
        lat=user.lat,
        lng=user.lng,
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
    user: User = Depends(require_role("BUYER")),
    db: AsyncSession = Depends(get_db)
):
    """Find matching lots for a demand."""
    result = await db.execute(select(BuyerDemand).where(BuyerDemand.id == demand_id))
    demand = result.scalar_one_or_none()
    
    if demand is None or demand.buyer_id != user.id:
        raise HTTPException(status_code=404, detail="Demand not found")

    lot_result = await db.execute(select(Lot).where(Lot.commodity_id == demand.commodity_id))
    lots = lot_result.scalars().all()
    
    # Use the matching engine
    matches_dict = matching_engine.match_lots_for_demand(lots, demand)
    return MatchesRes(**matches_dict)
