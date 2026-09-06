from fastapi import APIRouter, Depends
from sqlalchemy.ext.asyncio import AsyncSession
from app.database import get_db
from pydantic import BaseModel

router = APIRouter()

class BuyerReliabilityRes(BaseModel):
    successful_trades: int
    total_trades: int
    avg_payment_delay_hrs: float
    quality_dispute_rate: float

@router.get("/{buyer_id}/reliability", response_model=BuyerReliabilityRes)
async def get_buyer_reliability(buyer_id: int, db: AsyncSession = Depends(get_db)):
    """Get reliability metrics for a buyer."""
    # Stub response
    return BuyerReliabilityRes(
        successful_trades=42,
        total_trades=45,
        avg_payment_delay_hrs=2.5,
        quality_dispute_rate=0.05
    )
