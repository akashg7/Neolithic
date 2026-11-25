"""Sale-window (SELL / HOLD / NO_ADVICE) for an explicit crop, mandi and quantity.

Shared by `POST /ai/window/recommend`, `GET /lots/{id}/price-suggestion` and the
agent's `get_sale_window` tool. Unlike the old router body it never invents an
input:

* crop, mandi and quantity are required — no Onion / Lasalgaon / 5000 kg defaults;
* the spot price comes from the caller, else the latest observed mandi price,
  else the forecast model's p50 for today — never a hardcoded ₹2,200;
* distance is the real farm-to-mandi distance when a location is known; when it
  isn't, transport is left out and the result says so (`distance_source`).

The decision itself (refusal gate included) is untouched: it is
`window_engine.compute_sale_window`.
"""

from __future__ import annotations

from datetime import datetime

from sqlalchemy.ext.asyncio import AsyncSession

from app.engines.price_engine import price_engine
from app.engines.window_engine import compute_sale_window
from app.models.user import User
from app.services import price_service
from app.utils.haversine import haversine_km
from app.utils.id_resolver import RefEntity, load_catalog, resolve


_DATA_SOURCES = {"AGMARKNET", "MSAMB", "ARCHIVE", "IMPUTED", "SYNTHETIC"}


def anchored_quantiles(commodity_name: str, mandi_name: str,
                       spot_paise: int, horizon: int = 14) -> tuple[list[tuple[int, int, int]] | None, str]:
    """(p10, p50, p90) per day from the Maharashtra model, anchored on today's
    observed price. None → the decision falls back to the legacy per-crop model
    (and refuses with MODEL_UNAVAILABLE when that has no coverage either)."""
    try:
        rows = price_engine.predict_range(mandi_name, commodity_name, days=horizon,
                                          current_price_paise=spot_paise)
    except Exception:
        return None, "NONE"
    if not rows or rows[0].get("source") != "AGMARKNET_SOTA" or len(rows) < horizon:
        return None, "LEGACY"
    return [(int(r["p10_paise"]), int(r["p50_paise"]), int(r["p90_paise"])) for r in rows], "AGMARKNET_SOTA"


class WindowInputError(Exception):
    """A required input is missing (`missing` lists which)."""

    def __init__(self, missing: list[str]):
        self.missing = missing
        super().__init__("missing: " + ", ".join(missing))


class NoPriceDataError(Exception):
    """No observed price and no model forecast to anchor the decision on."""


async def _origin(db: AsyncSession, user: User | None,
                  lat: float | None, lng: float | None) -> tuple[float, float, str] | None:
    """Best known farm location: explicit → profile lat/lng → district mandi centroid."""
    if lat is not None and lng is not None:
        return lat, lng, "request"
    if user is not None and user.lat is not None and user.lng is not None:
        return user.lat, user.lng, "profile"
    if user is not None and user.district_id is not None:
        cat = await load_catalog(db)
        pts = [(m.lat, m.lng) for m in cat.all("market")
               if m.district_id == user.district_id and m.lat is not None and m.lng is not None]
        if pts:
            return (sum(p[0] for p in pts) / len(pts),
                    sum(p[1] for p in pts) / len(pts), "district")
    return None


async def spot_price(db: AsyncSession, commodity: RefEntity, market: RefEntity) -> tuple[int, str, str | None]:
    """(paise_per_qtl, source, obs_date) — observed price first, then model p50."""
    latest = await price_service.latest_price(db, commodity.id, market.id)
    if latest is not None:
        return latest["modal_paise_per_qtl"], latest["source"], latest["obs_date"]
    try:
        p = price_engine.predict(market.name, commodity.name, datetime.now().isoformat())
    except Exception:
        p = None
    if p and p.get("source") != "SYNTHETIC" and p.get("p50_paise"):
        return int(p["p50_paise"]), str(p.get("source", "MODEL")), None
    raise NoPriceDataError(f"no recent price for {commodity.name} at {market.name}")


async def sale_window(
    db: AsyncSession,
    *,
    commodity_ref: str | int | None,
    market_ref: str | int | None,
    quantity_kg: int | None,
    grade: str | None = None,
    user: User | None = None,
    current_price_paise: int | None = None,
    lat: float | None = None,
    lng: float | None = None,
    horizon_days: int = 14,
) -> dict:
    """Run the window engine on real inputs. Raises WindowInputError,
    ResolveError or NoPriceDataError instead of guessing."""
    missing = [name for name, v in (("crop", commodity_ref), ("mandi", market_ref),
                                    ("quantity_kg", quantity_kg)) if not v]
    if missing:
        raise WindowInputError(missing)
    if quantity_kg is not None and quantity_kg <= 0:
        raise WindowInputError(["quantity_kg"])

    commodity = await resolve(db, "commodity", commodity_ref)
    market = await resolve(db, "market", market_ref)

    # If this crop isn't traded at that mandi (no recent price), advise for the
    # nearest mandi that does trade it — the same rule as /market/overview —
    # rather than a model guess for a market that never sees the crop. The
    # reply names the mandi it used (`inputs.market`, `market_substituted`).
    requested_market = market
    if not current_price_paise and await price_service.latest_price(db, commodity.id, market.id) is None:
        cat = await load_catalog(db)
        traded = [cat.get("market", mid) for mid in await price_service.latest_prices_by_market(db, commodity.id)]
        traded = [m for m in traded if m is not None and m.lat is not None]
        if traded and market.lat is not None:
            market = min(traded, key=lambda m: haversine_km(market.lat, market.lng, m.lat, m.lng))

    if current_price_paise:
        spot, spot_source, spot_date = int(current_price_paise), "REQUEST", None
    else:
        spot, spot_source, spot_date = await spot_price(db, commodity, market)

    origin = await _origin(db, user, lat, lng)
    if origin is not None and market.lat is not None and market.lng is not None:
        distance_km = round(haversine_km(origin[0], origin[1], market.lat, market.lng), 1)
        distance_source = origin[2]
    else:
        distance_km = 0.0
        distance_source = "unknown"  # transport not included — said, not hidden

    # Only A/B/C mean something to the engine. A lot that hasn't been graded
    # yet arrives as "UNGRADED" (or nothing) and is priced as a B — the
    # mandi's middle grade — instead of failing the whole request.
    g = (grade or "").strip().upper()
    grade_used = g if g in ("A", "B", "C") else "B"

    quantiles, model_source = anchored_quantiles(commodity.name, market.name, spot)
    result = compute_sale_window(
        crop=commodity.name,
        mandi=market.name,
        quantity_kg=int(quantity_kg),
        current_price_mid_paise=spot,
        distance_km=distance_km,
        horizon_days=horizon_days,
        grade=grade_used,
        quantiles=quantiles,
    )
    # The badge the app shows is about the *price data* the decision rests on.
    result["data_source"] = spot_source if spot_source in _DATA_SOURCES else "IMPUTED"
    result["model_source"] = model_source
    result.setdefault("action", result.get("recommendation"))
    result.setdefault("costs", result.get("itemised_costs"))
    result["inputs"] = {
        "commodity": commodity.as_dict(),
        "market": market.as_dict(),
        "requested_market": requested_market.as_dict(),
        "market_substituted": market.id != requested_market.id,
        "quantity_kg": int(quantity_kg),
        "grade": grade_used,
        "spot_price_paise_per_qtl": spot,
        "spot_price_source": spot_source,
        "spot_price_date": spot_date,
        "distance_km": distance_km,
        "distance_source": distance_source,
        "transport_included": distance_source != "unknown",
    }
    return result
