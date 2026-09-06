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
    crop = payload.final_crop
    mandi = payload.final_mandi
    qty = payload.final_qty

    current_mid = payload.current_price_paise
    if not current_mid:
        try:
            today_fc = price_engine.predict(mandi, crop, "")
            current_mid = today_fc.get("p50_paise", 220000)
        except Exception:
            current_mid = 220000

    distance_km = 50.0

    result = compute_sale_window(
        crop=crop,
        mandi=mandi,
        quantity_kg=qty,
        current_price_mid_paise=current_mid,
        distance_km=distance_km,
        horizon_days=payload.horizon_days,
        grade=payload.grade
    )

    if "recommendation" in result and "action" not in result:
        result["action"] = result["recommendation"]
    if "itemised_costs" in result and "costs" not in result:
        result["costs"] = result["itemised_costs"]

    return WindowRes(**result)

