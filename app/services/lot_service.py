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
    comm_id = int(payload.commodity_id)
    mkt_id = int(payload.market_id) if payload.market_id else None
    wh_id = int(payload.warehouse_id) if payload.warehouse_id else None

    lot = Lot(
        farmer_id=user.id,
        commodity_id=comm_id,
        quantity_qtl=qty_qtl,
        expected_price_paise=payload.expected_price_paise,
        market_id=mkt_id,
        warehouse_id=wh_id,
        lat=user.lat,
        lng=user.lng,
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

    # Trigger async matching in background
    run_matching_engine_for_lot.delay(lot.id)

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
    """Get price band + sale window recommendation for a lot."""
    result = await db.execute(select(Lot).where(Lot.id == lot_id))
    lot = result.scalar_one_or_none()

    if lot is None or lot.farmer_id != user.id:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Lot not found")

    # Get commodity name
    comm_result = await db.execute(select(Commodity).where(Commodity.id == lot.commodity_id))
    commodity = comm_result.scalar_one_or_none()
    crop_name = commodity.name if commodity else "Unknown"

    lot_lat = lot.lat or 28.6139
    lot_lng = lot.lng or 77.2090

    nearest_mandi = await _find_nearest_mandi(db, lot_lat, lot_lng)
    mandi_name = nearest_mandi.name if nearest_mandi else "Azadpur"
    mandi_lat = nearest_mandi.lat if nearest_mandi else 28.7041
    mandi_lng = nearest_mandi.lng if nearest_mandi else 77.1025

    try:
        prediction = price_engine.predict(mandi_name, crop_name, datetime.now().isoformat())
        price_band = PriceBand(
            min_paise_per_qtl=prediction["p10_paise"],
            mid_paise_per_qtl=prediction["p50_paise"],
            max_paise_per_qtl=prediction["p90_paise"],
        )
    except Exception:
        price_band = PriceBand(min_paise_per_qtl=0, mid_paise_per_qtl=0, max_paise_per_qtl=0)

    distance_km = haversine_km(lot_lat, lot_lng, mandi_lat, mandi_lng)

    try:
        window_result = compute_sale_window(
            crop=crop_name,
            mandi=mandi_name,
            quantity_kg=lot.quantity_qtl * 100,
            current_price_mid_paise=lot.expected_price_paise or price_band.mid_paise_per_qtl or 200000,
            distance_km=distance_km,
        )
    except Exception:
        window_result = {
            "recommendation": "NO_ADVICE",
            "reason": "Unable to compute sale window at this time."
        }

    hold_until = None
    if window_result.get("hold_days"):
        hold_until = (datetime.now() + timedelta(days=window_result["hold_days"])).strftime("%Y-%m-%d")

    sale_window = SaleWindowInfo(
        recommendation=window_result.get("recommendation", "NO_ADVICE"),
        expected_gain_paise=window_result.get("expected_gain_paise"),
        worst_case_paise=window_result.get("worst_case_paise"),
        itemised_costs=window_result.get("itemised_costs"),
        hold_until_date=hold_until,
        reason=window_result.get("reason"),
    )

    return PriceSuggestionResponse(
        lot_id=lot.id,
        price_band=price_band,
        sale_window=sale_window,
    )


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
