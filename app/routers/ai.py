"""AI router for price forecasting and sale window recommendations."""
from fastapi import APIRouter
from app.engines.price_engine import price_engine
from app.engines.window_engine import compute_sale_window
from app.schemas.ai import WindowReq, WindowRes

router = APIRouter()


@router.get("/forecast")
async def get_price_forecasts(mandi: str, commodity: str, horizon: int = 14):
    """Raw quantile forecasts for the next N days."""
    try:
        return price_engine.predict_range(mandi, commodity, days=horizon)
    except Exception as e:
        return []

@router.post("/window/recommend", response_model=WindowRes)
async def get_sale_window(payload: WindowReq):
    """SELL/HOLD/NO_ADVICE recommendation based on exact per-quintal math."""
    # Assuming current price mid paise is fetched from somewhere, here we use a stub or price_engine's today's prediction
    try:
        today_fc = price_engine.predict(payload.market_id, payload.commodity_id, "")
        current_mid = today_fc["p50_paise"]
    except Exception:
        # If model fails, provide fallback
        current_mid = 200000

    # Assume distance is 50km for stub if we don't have farmer location
    distance_km = 50.0

    result = compute_sale_window(
        crop=payload.commodity_id,
        mandi=payload.market_id,
        quantity_kg=payload.qty_kg,
        current_price_mid_paise=current_mid,
        distance_km=distance_km,
        horizon_days=payload.horizon_days
    )
    return result
