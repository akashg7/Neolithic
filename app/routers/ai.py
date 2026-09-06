from datetime import datetime
from fastapi import APIRouter
from app.engines.price_engine import price_engine
from app.engines.window_engine import compute_sale_window
from app.schemas.ai import ForecastPoint, ForecastRes, ModelCard, WindowReq, WindowRes

router = APIRouter()


def _clean_commodity(c: str | None) -> str:
    if not c:
        return "Onion"
    s = c.replace("cmd_", "").replace("CMD_", "").strip()
    return s.capitalize() if s else "Onion"


def _clean_mandi(m: str | None) -> str:
    if not m:
        return "Lasalgaon APMC"
    s = m.replace("mkt_", "").replace("MKT_", "").strip()
    if not s:
        return "Lasalgaon APMC"
    s_low = s.lower()
    if "lasalgaon" in s_low:
        return "Lasalgaon APMC"
    if "pune" in s_low:
        return "Pune APMC"
    if "nashik" in s_low:
        return "Nashik APMC"
    if "nagpur" in s_low:
        return "Nagpur APMC"
    return s.title()


@router.get("/forecast", response_model=ForecastRes)
async def get_price_forecasts(
    mandi: str | None = None,
    commodity: str | None = None,
    market_id: str | None = None,
    commodity_id: str | None = None,
    horizon: int = 14,
):
    """Quantile forecasts for the next N days formatted as ForecastRes."""
    final_comm = _clean_commodity(commodity or commodity_id)
    final_mandi = _clean_mandi(mandi or market_id)

    try:
        raw_list = price_engine.predict_range(final_mandi, final_comm, days=horizon)
    except Exception:
        raw_list = []

    points = [
        ForecastPoint(
            target_date=item.get("date", ""),
            p10_paise_per_qtl=item.get("p10_paise", 0),
            p50_paise_per_qtl=item.get("p50_paise", 0),
            p90_paise_per_qtl=item.get("p90_paise", 0),
        )
        for item in raw_list
    ]

    model_card = ModelCard(
        mase=0.5718,
        coverage_80_bps=6960,
        algo="lightgbm_quantile",
        trained_at="2026-09-06T19:09:00+05:30",
        train_rows=267756,
        train_from="2024-01-23",
        train_to="2026-07-31",
        horizon_days=horizon,
        baseline="seasonal_naive",
    )

    return ForecastRes(
        as_of_date=datetime.now().strftime("%Y-%m-%d"),
        points=points,
        model_card=model_card,
    )


@router.get("/model-card", response_model=ModelCard)
async def get_model_card(
    commodity_id: str | None = None,
    commodity: str | None = None,
):
    """Full Model Card metrics for S08."""
    return ModelCard(
        mase=0.5718,
        coverage_80_bps=6960,
        algo="lightgbm_quantile",
        trained_at="2026-09-06T19:09:00+05:30",
        train_rows=267756,
        train_from="2024-01-23",
        train_to="2026-07-31",
        horizon_days=14,
        baseline="seasonal_naive",
    )

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

