from datetime import datetime
from app.ml.model_card import MODEL_CARD
from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.ext.asyncio import AsyncSession

from app.database import get_db
from app.dependencies.auth import get_optional_user
from app.engines.price_engine import price_engine
from app.models.user import User
from app.schemas.ai import ForecastPoint, ForecastRes, ModelCard, WindowReq, WindowRes
from app.services.window_service import NoPriceDataError, WindowInputError, sale_window
from app.utils.id_resolver import ResolveError, resolve
from app.services import price_service

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


async def _engine_name(db: AsyncSession, kind: str, ref: str | None) -> str | None:
    if not ref:
        return None
    try:
        return (await resolve(db, kind, ref)).name
    except ResolveError:
        return None
    except Exception:  # catalog unavailable (DB down) — keep the legacy path working
        return None


@router.get("/forecast", response_model=ForecastRes)
async def get_price_forecasts(
    mandi: str | None = None,
    commodity: str | None = None,
    market_id: str | None = None,
    commodity_id: str | None = None,
    horizon: int = 14,
    db: AsyncSession = Depends(get_db),
):
    """Quantile forecasts for the next N days formatted as ForecastRes.

    Accepts slug, integer id or name; resolved to the DB name the models were
    trained on. Unresolvable values fall back to the legacy string cleanup.
    """
    final_comm = await _engine_name(db, "commodity", commodity or commodity_id) or _clean_commodity(commodity or commodity_id)
    final_mandi = await _engine_name(db, "market", mandi or market_id) or _clean_mandi(mandi or market_id)

    # Anchor the trajectory on today's observed mandi price when we have one.
    anchor = None
    try:
        c = await resolve(db, "commodity", commodity or commodity_id)
        m = await resolve(db, "market", mandi or market_id)
        latest = await price_service.latest_price(db, c.id, m.id)
        anchor = latest["modal_paise_per_qtl"] if latest else None
    except Exception:
        anchor = None

    try:
        raw_list = price_engine.predict_range(final_mandi, final_comm, days=horizon,
                                              current_price_paise=anchor)
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

    model_card = ModelCard(**MODEL_CARD, horizon_days=horizon)

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
    return ModelCard(**MODEL_CARD, horizon_days=14)

@router.post("/window/recommend", response_model=WindowRes)
async def get_sale_window(
    payload: WindowReq,
    db: AsyncSession = Depends(get_db),
    user: User | None = Depends(get_optional_user),
):
    """SELL/HOLD/NO_ADVICE recommendation on real inputs.

    Crop, mandi and quantity are required (no silent Onion/Lasalgaon/5000 kg
    defaults); distance comes from the caller's profile location; the spot price
    is the latest observed mandi price unless the caller supplies one.
    """
    try:
        result = await sale_window(
            db,
            commodity_ref=payload.commodity_id or payload.crop,
            market_ref=payload.market_id or payload.mandi,
            quantity_kg=payload.qty_kg or payload.quantity_kg,
            grade=payload.grade,
            user=user,
            current_price_paise=payload.current_price_paise,
            horizon_days=payload.horizon_days,
        )
    except WindowInputError as exc:
        raise HTTPException(status_code=400, detail=f"Missing required field(s): {', '.join(exc.missing)}") from exc
    except ResolveError as exc:
        raise HTTPException(status_code=404, detail=str(exc)) from exc
    except NoPriceDataError:
        return WindowRes(
            action="NO_ADVICE", confidence="LOW", band_width_bps=0,
            model_card=ModelCard(), data_source="NONE", refusal_reason="STALE_DATA",
            explain_mr="या पिकासाठी या बाजारात अलीकडचा भाव उपलब्ध नाही, म्हणून सल्ला देता येत नाही.",
            explain_en="No recent price for this crop at this mandi, so we can't advise.",
        )

    result.pop("inputs", None)
    return WindowRes(**result)
