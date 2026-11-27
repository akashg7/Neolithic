"""Market overview — everything the Home (S04) and Market (PricesIndex) screens
show for one crop at one mandi, in one round trip, computed from real data:

  latest observed rate, 30-day history, 7-day trend, the model's 14-day fan
  (anchored on today's observed rate), the sell/hold verdict for a reference
  quantity, and nearby mandis ranked by net take-home price.

Every number carries its source; nothing here is generated client-side.
"""

from __future__ import annotations

from typing import Optional

from fastapi import APIRouter, Depends, HTTPException, Query
from sqlalchemy.ext.asyncio import AsyncSession

from app.database import get_db
from app.dependencies.auth import get_optional_user
from app.models.user import User
from app.services import price_service
from app.services.window_service import NoPriceDataError, sale_window
from app.utils.cache import safe_cache
from app.utils.id_resolver import resolve_or_404

router = APIRouter()


@router.get("/overview")
@safe_cache(expire=300, namespace="market", user_scoped=True)
async def market_overview(
    commodity_id: str,
    market_id: str,
    district_id: Optional[str] = None,
    qty_kg: int = Query(1000, ge=100, le=1_000_000, description="Reference lot for the verdict"),
    db: AsyncSession = Depends(get_db),
    user: Optional[User] = Depends(get_optional_user),
) -> dict:
    commodity = await resolve_or_404(db, "commodity", commodity_id, "commodity_id")
    market = await resolve_or_404(db, "market", market_id, "market_id")
    district = await resolve_or_404(db, "district", district_id, "district_id") if district_id else None

    requested_market = market
    series = await price_service.price_series(db, commodity.id, market.id, days=30)
    points = series["points"]
    if not points:
        # This crop isn't traded at that mandi: use the nearest mandi that has a
        # recent price for it, and say so (`market_substituted`).
        from app.utils.haversine import haversine_km
        from app.utils.id_resolver import load_catalog
        cat = await load_catalog(db)
        candidates = [cat.get("market", mid) for mid in await price_service.latest_prices_by_market(db, commodity.id)]
        candidates = [m for m in candidates if m is not None and m.lat is not None]
        if not candidates or requested_market.lat is None:
            raise HTTPException(status_code=404, detail=f"No recent price data for {commodity.name}")
        market = min(candidates, key=lambda m: haversine_km(requested_market.lat, requested_market.lng, m.lat, m.lng))
        series = await price_service.price_series(db, commodity.id, market.id, days=30)
        points = series["points"]
    latest = points[-1]
    snap = await price_service.mandi_snapshot(db, commodity.id, market.id) or {}
    modal_30 = [p["modal_paise_per_qtl"] for p in points]

    fc = price_service.forecast(commodity.name, market.name, 14,
                                current_price_paise=latest["modal_paise_per_qtl"])

    try:
        w = await sale_window(db, commodity_ref=commodity.id, market_ref=market.id,
                              quantity_kg=qty_kg, user=user)
        verdict = {k: w.get(k) for k in (
            "action", "confidence", "hold_days", "band_width_bps", "expected_gain_paise",
            "worst_case_paise", "sell_now_net_paise_per_qtl", "hold_p50_net_paise_per_qtl",
            "refusal_reason", "explain_mr", "explain_en", "data_source", "model_source",
            "itemised_costs")}
        verdict["quantity_kg"] = qty_kg
    except NoPriceDataError:
        verdict = {"action": "NO_ADVICE", "refusal_reason": "STALE_DATA",
                   "explain_mr": "अलीकडचा भाव उपलब्ध नाही.", "explain_en": "No recent price.",
                   "quantity_kg": qty_kg}

    district_db_id = district.id if district else (user.district_id if user else market.district_id)
    origin = (user.lat, user.lng) if (user and user.lat is not None and user.lng is not None) \
        else await price_service.district_centroid(db, district_db_id) if district_db_id else None
    nearby = await price_service.nearby_markets(db, commodity.id, origin=origin,
                                                from_district_id=district_db_id)

    return {
        "commodity": commodity.as_dict(),
        "market": market.as_dict(),
        "requested_market": requested_market.as_dict(),
        "market_substituted": market.id != requested_market.id,
        "latest": latest,
        # Range of the daily *modal* rate, same basis as the average. The
        # per-day min/max are single outlier trades (e.g. a damaged lot at
        # ₹600 on a ₹4,600 day) and would mislead as a "30-day low".
        "min_30d_paise_per_qtl": min(modal_30),
        "max_30d_paise_per_qtl": max(modal_30),
        "avg_30d_paise_per_qtl": sum(modal_30) // len(modal_30),
        "change_7d_paise_per_qtl": snap.get("change_paise_per_qtl"),
        "change_7d_bps": snap.get("change_bps"),
        "history": points,
        "source_summary": series["source_summary"],
        "forecast": fc,
        "verdict": verdict,
        "nearby": nearby,
    }
