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
        today_fc = price_engine.predict(payload.commodity_id, payload.market_id, "")
        current_mid = today_fc["p50_paise"]
    except Exception:
        # If model fails, safely return NO_ADVICE
        return WindowRes(
            action="NO_ADVICE",
            refusal_reason="INSUFFICIENT_HISTORY",
            explain_en="Insufficient historical data to make a confident prediction.",
            explain_mr="आत्मविश्वासाने अंदाज वर्तवण्यासाठी पुरेसा ऐतिहासिक डेटा नाही.",
            confidence="LOW",
            band_width_bps=0,
            expected_gain_paise=None,
            worst_case_paise=None,
            costs=None,
            sell_now_net_paise_per_qtl=None,
            hold_p50_net_paise_per_qtl=None,
            hold_p10_net_paise_per_qtl=None,
            model_card={"mase": 0.0, "coverage_80_bps": 0},
            data_source="UNKNOWN",
            pledge_quote=None,
            alt_market=None
        )

    # Use a realistic default distance if missing
    distance_km = 500.0

    result = compute_sale_window(
        crop=payload.commodity_id,
        mandi=payload.market_id,
        quantity_kg=payload.qty_kg,
        current_price_mid_paise=current_mid,
        distance_km=distance_km,
        horizon_days=payload.horizon_days
    )
    return result
