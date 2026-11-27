"""Price reads shared by the /prices router and the agent tools.

All money is integer paise per quintal. Every result names its source
(`AGMARKNET`, `MSAMB`, `ARCHIVE`, `IMPUTED`, `SYNTHETIC`) so nothing invented can
be passed off as observed.
"""

from __future__ import annotations

from datetime import datetime, timedelta, timezone

from sqlalchemy import select, tuple_
from sqlalchemy.ext.asyncio import AsyncSession

from app.engines.price_engine import price_engine
from app.models.mandi import MandiLocation, PriceObservation
from app.utils.spatial import distance_km_expr, is_postgres, within_radius_filter

_KNOWN_SOURCES = {"AGMARKNET", "MSAMB", "ARCHIVE", "IMPUTED", "SYNTHETIC"}


def _source(obs: PriceObservation) -> str:
    return obs.observation_type if obs.observation_type in _KNOWN_SOURCES else "IMPUTED"


def _point(obs: PriceObservation) -> dict:
    return {
        "obs_date": obs.date.strftime("%Y-%m-%d"),
        "min_paise_per_qtl": obs.min_price_paise or obs.modal_price_paise,
        "max_paise_per_qtl": obs.max_price_paise or obs.modal_price_paise,
        "modal_paise_per_qtl": obs.modal_price_paise,
        "arrivals_qtl": obs.arrivals_qtl or 0,
        "source": _source(obs),
    }


async def price_series(db: AsyncSession, commodity_id: int, market_id: int, days: int = 180) -> dict:
    """Daily observations, oldest first, in the `PriceSeriesRes` shape."""
    start = datetime.now(timezone.utc) - timedelta(days=days)
    rows = (await db.execute(
        select(PriceObservation)
        .where(PriceObservation.commodity_id == commodity_id)
        .where(PriceObservation.market_id == market_id)
        .where(PriceObservation.date >= start)
        .order_by(PriceObservation.date.asc())
    )).scalars().all()

    points = [_point(o) for o in rows]
    summary: dict[str, int] = {}
    for p in points:
        summary[p["source"]] = summary.get(p["source"], 0) + 1
    latest = points[-1]["obs_date"] if points else datetime.now().strftime("%Y-%m-%d")
    return {"points": points, "source_summary": summary, "latest_obs_date": latest}


async def latest_price(db: AsyncSession, commodity_id: int, market_id: int,
                       max_age_days: int = 30) -> dict | None:
    """Most recent observation within `max_age_days`, or None."""
    since = datetime.now(timezone.utc) - timedelta(days=max_age_days)
    obs = (await db.execute(
        select(PriceObservation)
        .where(PriceObservation.commodity_id == commodity_id)
        .where(PriceObservation.market_id == market_id)
        .where(PriceObservation.date >= since)
        .order_by(PriceObservation.date.desc())
        .limit(1)
    )).scalar_one_or_none()
    return _point(obs) if obs else None


async def mandi_snapshot(db: AsyncSession, commodity_id: int, market_id: int,
                         compare_days: int = 7) -> dict | None:
    """Latest rate plus its change against the observation ~`compare_days` earlier.

    Returns None when there is no observation in the last 30 days.
    """
    latest = await latest_price(db, commodity_id, market_id)
    if latest is None:
        return None
    latest_dt = datetime.strptime(latest["obs_date"], "%Y-%m-%d").replace(tzinfo=timezone.utc)
    prior = (await db.execute(
        select(PriceObservation)
        .where(PriceObservation.commodity_id == commodity_id)
        .where(PriceObservation.market_id == market_id)
        .where(PriceObservation.date <= latest_dt - timedelta(days=compare_days))
        .order_by(PriceObservation.date.desc())
        .limit(1)
    )).scalar_one_or_none()

    snap = dict(latest)
    if prior is not None and prior.modal_price_paise:
        change = latest["modal_paise_per_qtl"] - prior.modal_price_paise
        snap["prev_obs_date"] = prior.date.strftime("%Y-%m-%d")
        snap["prev_modal_paise_per_qtl"] = prior.modal_price_paise
        snap["change_paise_per_qtl"] = change
        snap["change_bps"] = change * 10_000 // prior.modal_price_paise
    else:
        snap["prev_obs_date"] = None
        snap["prev_modal_paise_per_qtl"] = None
        snap["change_paise_per_qtl"] = None
        snap["change_bps"] = None
    return snap


def forecast(commodity_name: str, mandi_name: str, horizon_days: int = 14,
             current_price_paise: int | None = None) -> dict:
    """Quantile forecast from the price engine, with an honest source label.

    `is_model` is False when the engine fell back to its SYNTHETIC stub; callers
    that give advice must not present those numbers as a forecast.
    """
    try:
        raw = price_engine.predict_range(mandi_name, commodity_name, days=horizon_days,
                                         current_price_paise=current_price_paise)
    except Exception:
        raw = []
    points = [
        {
            "target_date": r.get("date", ""),
            "p10_paise_per_qtl": int(r.get("p10_paise", 0)),
            "p50_paise_per_qtl": int(r.get("p50_paise", 0)),
            "p90_paise_per_qtl": int(r.get("p90_paise", 0)),
        }
        for r in raw
    ]
    sources = {r.get("source", "SYNTHETIC") for r in raw}
    source = sources.pop() if len(sources) == 1 else ("MIXED" if sources else "NONE")
    return {
        "points": points,
        "source": source,
        "is_model": bool(points) and source not in ("SYNTHETIC", "NONE", "MIXED"),
    }


# ── nearby mandis, ranked by what the farmer actually takes home ───────────

# Fallback transport when no seeded route exists: a 10-tonne truck at ~₹40/km
# spread over 100 quintals ≈ 40 paise per quintal per km. Rows using it say so
# (`transport_source = "IMPUTED"`).
NEARBY_TRANSPORT_PAISE_PER_QTL_KM = 40


async def latest_prices_by_market(db: AsyncSession, commodity_id: int,
                                  max_age_days: int = 30) -> dict[int, dict]:
    """market_id -> latest observation point, one query (DISTINCT ON)."""
    since = datetime.now(timezone.utc) - timedelta(days=max_age_days)
    rows = (await db.execute(
        select(PriceObservation)
        .where(PriceObservation.commodity_id == commodity_id)
        .where(PriceObservation.date >= since)
        .where(PriceObservation.market_id.is_not(None))
        .order_by(PriceObservation.market_id, PriceObservation.date.desc())
        .distinct(PriceObservation.market_id)
    )).scalars().all()
    return {o.market_id: _point(o) for o in rows}


async def latest_prices_for_pairs(
    db: AsyncSession,
    pairs: set[tuple[int, int]],
    max_age_days: int = 30,
) -> dict[tuple[int, int], dict]:
    """Batch lookup of latest observation per (commodity_id, market_id) in one query."""
    if not pairs:
        return {}
    since = datetime.now(timezone.utc) - timedelta(days=max_age_days)
    stmt = (
        select(PriceObservation)
        .where(tuple_(PriceObservation.commodity_id, PriceObservation.market_id).in_(list(pairs)))
        .where(PriceObservation.date >= since)
        .order_by(PriceObservation.commodity_id, PriceObservation.market_id, PriceObservation.date.desc())
    )
    if is_postgres(db):
        stmt = stmt.distinct(PriceObservation.commodity_id, PriceObservation.market_id)
        rows = (await db.execute(stmt)).scalars().all()
        return {(o.commodity_id, o.market_id): _point(o) for o in rows}
    rows = (await db.execute(stmt)).scalars().all()
    out: dict[tuple[int, int], dict] = {}
    for o in rows:
        k = (o.commodity_id, o.market_id)
        if k not in out:
            out[k] = _point(o)
    return out


async def nearby_markets(db: AsyncSession, commodity_id: int, *,
                         origin: tuple[float, float] | None,
                         from_district_id: int | None,
                         radius_km: float = 250, limit: int = 8) -> dict:
    """Mandis with a recent price for this crop, ranked by net ₹/qtl after
    transport, commission and loading (NearbyRes shape)."""
    from app.domain.constants import COMMISSION_RATE_BPS, LOADING_PAISE_PER_KG
    from app.models.reference import LogisticsCostRoute
    from app.utils.haversine import haversine_km
    from app.utils.id_resolver import load_catalog

    catalog = await load_catalog(db)
    routes = {}
    if from_district_id is not None:
        for r in (await db.execute(select(LogisticsCostRoute).where(
                LogisticsCostRoute.from_district_id == from_district_id))).scalars():
            routes[r.to_market_id] = r

    candidates: list[tuple[int, dict, float | None]] = []
    if is_postgres(db) and origin is not None:
        since = datetime.now(timezone.utc) - timedelta(days=30)
        latest_subq = (
            select(
                PriceObservation.market_id.label("market_id"),
                PriceObservation.date.label("date"),
                PriceObservation.min_price_paise.label("min_price_paise"),
                PriceObservation.max_price_paise.label("max_price_paise"),
                PriceObservation.modal_price_paise.label("modal_price_paise"),
                PriceObservation.arrivals_qtl.label("arrivals_qtl"),
                PriceObservation.observation_type.label("observation_type"),
            )
            .where(PriceObservation.commodity_id == commodity_id)
            .where(PriceObservation.date >= since)
            .where(PriceObservation.market_id.is_not(None))
            .order_by(PriceObservation.market_id, PriceObservation.date.desc())
            .distinct(PriceObservation.market_id)
            .subquery()
        )
        dist_col = distance_km_expr(MandiLocation.geom, origin[0], origin[1]).label("distance_km")
        pg_rows = (
            await db.execute(
                select(latest_subq, dist_col)
                .join(MandiLocation, MandiLocation.id == latest_subq.c.market_id)
                .where(within_radius_filter(MandiLocation.geom, origin[0], origin[1], radius_km))
            )
        ).all()
        for row in pg_rows:
            src = row.observation_type if row.observation_type in _KNOWN_SOURCES else "IMPUTED"
            point = {
                "obs_date": row.date.strftime("%Y-%m-%d"),
                "min_paise_per_qtl": row.min_price_paise or row.modal_price_paise,
                "max_paise_per_qtl": row.max_price_paise or row.modal_price_paise,
                "modal_paise_per_qtl": row.modal_price_paise,
                "arrivals_qtl": row.arrivals_qtl or 0,
                "source": src,
            }
            candidates.append((row.market_id, point, round(float(row.distance_km), 1)))
    else:
        latest = await latest_prices_by_market(db, commodity_id)
        for market_id, p in latest.items():
            m = catalog.get("market", market_id)
            if m is None or m.lat is None:
                continue
            dist = round(haversine_km(origin[0], origin[1], m.lat, m.lng), 1) if origin else None
            if dist is not None and dist > radius_km:
                continue
            candidates.append((market_id, p, dist))

    rows = []
    for market_id, p, dist in candidates:
        m = catalog.get("market", market_id)
        if m is None or m.lat is None:
            continue
        gross = p["modal_paise_per_qtl"]
        route = routes.get(market_id)
        if route is not None:
            transport = route.transport_paise_per_qtl
            commission = gross * route.commission_bps // 10_000
            loading = route.loading_paise_per_qtl
            transport_source = route.source
        else:
            transport = int(round((dist or 0) * NEARBY_TRANSPORT_PAISE_PER_QTL_KM))
            commission = gross * COMMISSION_RATE_BPS // 10_000
            loading = LOADING_PAISE_PER_KG * 100
            transport_source = "IMPUTED"
        rows.append({
            "market_id": m.slug, "name": m.name, "name_mr": m.name_mr,
            "gross_paise_per_qtl": gross,
            "transport_paise_per_qtl": transport,
            "commission_paise_per_qtl": commission,
            "loading_paise_per_qtl": loading,
            "net_paise_per_qtl": gross - transport - commission - loading,
            "distance_km": dist if dist is not None else 0.0,
            "source": p["source"],
            "transport_source": transport_source,
            "obs_date": p["obs_date"],
        })
    rows.sort(key=lambda r: r["net_paise_per_qtl"], reverse=True)
    as_of = max((r["obs_date"] for r in rows), default=datetime.now().strftime("%Y-%m-%d"))
    return {"as_of_date": as_of, "rows": rows[:limit], "sorted_by": "net_paise_per_qtl"}


async def district_centroid(db: AsyncSession, district_id: int) -> tuple[float, float] | None:
    from app.utils.id_resolver import load_catalog
    cat = await load_catalog(db)
    pts = [(m.lat, m.lng) for m in cat.all("market") if m.district_id == district_id and m.lat is not None]
    if not pts:
        return None
    return sum(p[0] for p in pts) / len(pts), sum(p[1] for p in pts) / len(pts)
