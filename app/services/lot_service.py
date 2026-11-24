from datetime import datetime, timedelta
from typing import Optional

from fastapi import HTTPException, status
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import selectinload

from app.models.user import User
from app.models.lot import Lot, BatchLotMember
from app.models.mandi import MandiLocation
from app.models.demand import BuyerDemand
from app.models.reference import Commodity
from app.worker import run_matching_engine_for_lot
from app.engines.grading_engine import grade as compute_grade
from app.engines.price_engine import price_engine
from app.engines.window_engine import compute_sale_window
from app.utils.haversine import haversine_km
from app.utils.id_resolver import resolve_or_404, load_catalog
from app.services.window_service import sale_window, NoPriceDataError
from app.schemas.lot import (
    LotCreate, LotOut, SelfAssayRequest, SelfAssayResponse,
    PriceSuggestionResponse, PriceBand, SaleWindowInfo,
)
from app.schemas.matches import MatchesRes
from app.engines import matching_engine


async def _find_nearest_mandi(db: AsyncSession, lat: float, lng: float) -> Optional[MandiLocation]:
    """Find the nearest mandi location to the given coordinates."""
    result = await db.execute(select(MandiLocation))
    mandis = result.scalars().all()
    if not mandis:
        return None

    nearest = min(mandis, key=lambda m: haversine_km(lat, lng, m.lat, m.lng))
    return nearest


async def create_lot(db: AsyncSession, user: User, payload: LotCreate) -> LotOut:
    """Create a new lot."""
    qty_qtl = payload.quantity_qtl if payload.quantity_qtl is not None else (payload.qty_kg // 100 if payload.qty_kg else 10)
    # Accept the app's slugs ("cmd_onion", "mkt_lasalgaon") as well as integer ids.
    comm_id = (await resolve_or_404(db, "commodity", payload.commodity_id, "commodity_id")).id
    mkt_id = (await resolve_or_404(db, "market", payload.market_id, "market_id")).id if payload.market_id else None
    wh_id = int(payload.warehouse_id) if payload.warehouse_id and str(payload.warehouse_id).isdigit() else None

    lot = Lot(
        farmer_id=user.id,
        commodity_id=comm_id,
        quantity_qtl=qty_qtl,
        expected_price_paise=payload.expected_price_paise,
        market_id=mkt_id,
        warehouse_id=wh_id,
        lat=user.lat,
        lng=user.lng,
        image_url=payload.photo_path,
        status="active",
    )


    if payload.self_assay:
        try:
            grade_result = compute_grade(payload.self_assay)
            lot.self_assay_answers = payload.self_assay
            lot.grade = grade_result["grade"]
        except Exception:
            pass

    db.add(lot)
    await db.commit()
    await db.refresh(lot)

    # Trigger async matching in background. Best effort: a broker outage must
    # not fail a lot the farmer has already saved (the task is a no-op today).
    try:
        run_matching_engine_for_lot.delay(lot.id)
    except Exception:
        pass

    return LotOut.model_validate(lot)


async def get_lot(db: AsyncSession, user: User, lot_id: int) -> LotOut:
    """Get a single lot. Validates ownership or buyer-has-offer access."""
    result = await db.execute(select(Lot).where(Lot.id == lot_id))
    lot = result.scalar_one_or_none()

    if lot is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Lot not found")

    # Access control: farmer who owns it, or buyer with an active offer
    if lot.farmer_id != user.id:
        # Check if the user is a buyer with an offer on this lot
        from app.models.offer import OfferLot, Offer
        offer_check = await db.execute(
            select(OfferLot)
            .join(Offer)
            .where(OfferLot.lot_id == lot_id)
            .where(Offer.buyer_id == user.id)
            .where(Offer.status.in_(["pending", "accepted", "paid"]))
        )
        if offer_check.scalar_one_or_none() is None:
            raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Lot not found")

    return LotOut.model_validate(lot)


async def list_lots(db: AsyncSession, user: User, status_filter: Optional[str] = None) -> list[LotOut]:
    """List lots owned by the current farmer, optionally filtered by status."""
    query = select(Lot).where(Lot.farmer_id == user.id)
    if status_filter:
        query = query.where(Lot.status == status_filter)
    query = query.order_by(Lot.created_at.desc())

    result = await db.execute(query)
    lots = result.scalars().all()
    return [LotOut.model_validate(lot) for lot in lots]


async def submit_self_assay(
    db: AsyncSession, user: User, lot_id: int, answers: SelfAssayRequest
) -> SelfAssayResponse:
    """Submit self-assay answers and compute grade."""
    result = await db.execute(select(Lot).where(Lot.id == lot_id))
    lot = result.scalar_one_or_none()

    if lot is None or lot.farmer_id != user.id:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Lot not found")

    # Save answers and compute grade
    answers_dict = answers.model_dump()
    grade_result = compute_grade(answers_dict)

    lot.self_assay_answers = answers_dict
    lot.grade = grade_result["grade"]

    await db.commit()

    return SelfAssayResponse(
        lot_id=str(lot.id),
        score=grade_result["score"],
        grade=grade_result["grade"],
        weakest_dimension=grade_result["weakest_dimension"],
        tip_mr=grade_result["tip_mr"],
        tip_en=grade_result["tip_en"],
        self_assay_answers=answers_dict,
    )



async def get_price_suggestion(db: AsyncSession, user: User, lot_id: int) -> PriceSuggestionResponse:
    """Price band + sale-window recommendation for a lot.

    The mandi is the lot's own market, else the mandi nearest the lot, else the
    mandi nearest the farmer's profile location. With none of those there is no
    honest answer, so the window says NO_ADVICE (no Delhi/Azadpur fallback).
    """
    lot = (await db.execute(select(Lot).where(Lot.id == lot_id))).scalar_one_or_none()
    if lot is None or lot.farmer_id != user.id:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Lot not found")

    catalog = await load_catalog(db)
    commodity = catalog.get("commodity", lot.commodity_id)
    market = catalog.get("market", lot.market_id) if lot.market_id else None
    if market is None:
        lat = lot.lat if lot.lat is not None else user.lat
        lng = lot.lng if lot.lng is not None else user.lng
        if lat is not None and lng is not None:
            nearest = await _find_nearest_mandi(db, lat, lng)
            market = catalog.get("market", nearest.id) if nearest else None

    no_band = PriceBand(min_paise_per_qtl=0, mid_paise_per_qtl=0, max_paise_per_qtl=0, band_source="NONE")
    if commodity is None or market is None:
        return PriceSuggestionResponse(
            lot_id=str(lot.id), price_band=no_band,
            sale_window=SaleWindowInfo(recommendation="NO_ADVICE",
                                       reason="Lot has no mandi and no location to find one."),
        )

    # Band = tomorrow's p10/p50/p90 from the model, anchored on today's observed
    # mandi price (the unanchored engine starts from a crop default instead).
    from app.services import price_service
    latest = await price_service.latest_price(db, commodity.id, market.id)
    fc = price_service.forecast(commodity.name, market.name, 1,
                                current_price_paise=latest["modal_paise_per_qtl"] if latest else None)
    if fc["is_model"] and latest:
        p0 = fc["points"][0]
        price_band = PriceBand(min_paise_per_qtl=p0["p10_paise_per_qtl"],
                               mid_paise_per_qtl=p0["p50_paise_per_qtl"],
                               max_paise_per_qtl=p0["p90_paise_per_qtl"],
                               band_source=fc["source"])
    else:
        price_band = no_band

    try:
        window_result = await sale_window(
            db,
            commodity_ref=commodity.id,
            market_ref=market.id,
            quantity_kg=lot.quantity_qtl * 100,
            grade=lot.grade if lot.grade in ("A", "B", "C") else None,
            user=user,
            current_price_paise=lot.expected_price_paise,
            lat=lot.lat, lng=lot.lng,
        )
    except NoPriceDataError:
        window_result = {"recommendation": "NO_ADVICE",
                         "reason": "No recent price for this crop at this mandi."}
    except Exception:
        window_result = {"recommendation": "NO_ADVICE",
                         "reason": "Unable to compute sale window at this time."}

    hold_until = None
    if window_result.get("hold_days"):
        hold_until = (datetime.now() + timedelta(days=window_result["hold_days"])).strftime("%Y-%m-%d")

    sale_window_info = SaleWindowInfo(
        recommendation=window_result.get("recommendation", "NO_ADVICE"),
        expected_gain_paise=window_result.get("expected_gain_paise"),
        worst_case_paise=window_result.get("worst_case_paise"),
        itemised_costs=window_result.get("itemised_costs"),
        hold_until_date=hold_until,
        reason=window_result.get("reason") or window_result.get("refusal_reason"),
    )

    return PriceSuggestionResponse(
        lot_id=str(lot.id),
        price_band=price_band,
        sale_window=sale_window_info,
        market_id=market.slug,
        market_slug=market.slug,
    )


async def get_lot_assay(db: AsyncSession, user: User, lot_id: int) -> dict:
    """Stored self-assay answers + the grade they produce. Same access rule as get_lot."""
    await get_lot(db, user, lot_id)  # 404 unless owner or buyer-with-offer
    lot = await db.get(Lot, lot_id)
    answers = lot.self_assay_answers or {}
    required = ("size_uniform", "colour_uniform", "sprouting", "damage_pct", "moisture_feel", "foreign_matter")
    if not all(k in answers for k in required):
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Lot has no assay yet")
    g = compute_grade(answers)
    return {
        "lot_id": str(lot.id), **{k: int(answers[k]) for k in required},
        "score": g["score"], "grade": g["grade"], "weakest_dimension": g["weakest_dimension"],
        "tip_mr": g["tip_mr"], "tip_en": g["tip_en"],
        "photo_path": lot.image_url,
        "created_at": lot.created_at.isoformat() if lot.created_at else None,
    }


async def publish_lot(db: AsyncSession, user: User, lot_id: int, price_paise: int) -> LotOut:
    """Set the asking price and (re)list the lot. Owner only; sold/pooled lots can't be relisted."""
    lot = await db.get(Lot, lot_id)
    if lot is None or lot.farmer_id != user.id:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Lot not found")
    if (lot.status or "active").lower() != "active":
        raise HTTPException(status_code=status.HTTP_409_CONFLICT,
                            detail=f"Lot is {lot.status}; only an active lot can be published")
    lot.expected_price_paise = price_paise
    await db.commit()
    await db.refresh(lot)
    return LotOut.model_validate(lot)


async def get_lot_matches(db: AsyncSession, user: User, lot_id: int) -> dict:
    """Find matching buyer demands for a lot. Returns MatchesRes format dict."""
    result = await db.execute(select(Lot).where(Lot.id == lot_id))
    lot = result.scalar_one_or_none()

    if lot is None or lot.farmer_id != user.id:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Lot not found")

    demand_result = await db.execute(select(BuyerDemand).where(BuyerDemand.commodity_id == lot.commodity_id))
    demands = demand_result.scalars().all()

    matches_dict = matching_engine.match_demands_for_lot(demands, lot)
    return matches_dict
