"""AI router — stub for Nikhil to implement."""
from fastapi import APIRouter
from fastapi_cache.decorator import cache

router = APIRouter()


# TODO: Nikhil implements these endpoints
# GET /ai/price-forecast?mandi=&commodity= — raw quantile forecasts
@router.get("/price-forecast")
@cache(expire=3600)
async def get_price_forecasts():
    return []

# GET /ai/sale-window?lot_id= — SELL/HOLD/NO_ADVICE recommendation
@router.get("/sale-window")
@cache(expire=3600)
async def get_sale_window():
    return {}
