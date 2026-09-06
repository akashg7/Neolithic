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
from app.worker import run_matching_engine_for_lot
from app.engines.grading_engine import grade as compute_grade
from app.engines.price_engine import price_engine
from app.engines.window_engine import compute_sale_window
from app.engines.matching_engine import match_demands_for_lot
from app.utils.haversine import haversine_km
from app.schemas.lot import (
    LotCreate, LotOut, SelfAssayRequest, SelfAssayResponse,
    PriceSuggestionResponse, PriceBand, SaleWindowInfo,
    LotMatchesResponse, MatchResult,
)


async def _find_nearest_mandi(db: AsyncSession, lat: float, lng: float) -> Optional[MandiLocation]:
    """Find the nearest mandi location to the given coordinates."""
    result = await db.execute(select(MandiLocation))
    mandis = result.scalars().all()
    if not mandis:
        return None

    nearest = min(mandis, key=lambda m: haversine_km(lat, lng, m.lat, m.lng))
    return nearest


async def create_lot(db: AsyncSession, user: User, payload: LotCreate) -> LotOut:
    """Create a new lot with price band from the price engine."""
    lot = Lot(
        farmer_id=user.id,
        crop=payload.crop,
        quantity_kg=payload.quantity_kg,
        lat=payload.lat or user.lat,
        lng=payload.lng or user.lng,
        image_url=payload.image_url,
        status="active",
    )

    # Try to get price prediction
    lot_lat = lot.lat or 28.6139  # Default to Delhi
    lot_lng = lot.lng or 77.2090

    nearest_mandi = await _find_nearest_mandi(db, lot_lat, lot_lng)
    mandi_name = nearest_mandi.name if nearest_mandi else "Azadpur"

    try:
        prediction = price_engine.predict(mandi_name, payload.crop, datetime.now().isoformat())
        lot.price_min_paise_per_qtl = prediction["p10_paise"]
        lot.price_mid_paise_per_qtl = prediction["p50_paise"]
        lot.price_max_paise_per_qtl = prediction["p90_paise"]
    except Exception:
        # Price engine may not be loaded — that's OK for now
        pass

    db.add(lot)
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

    await db.flush()

    return SelfAssayResponse(
        lot_id=lot.id,
        grade=grade_result["grade"],
        improvement_tip=grade_result["improvement_tip"],
        self_assay_answers=answers_dict,
    )


async def get_price_suggestion(db: AsyncSession, user: User, lot_id: int) -> PriceSuggestionResponse:
    """Get price band + sale window recommendation for a lot."""
    result = await db.execute(select(Lot).where(Lot.id == lot_id))
    lot = result.scalar_one_or_none()

    if lot is None or lot.farmer_id != user.id:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Lot not found")

    # Build price band
    price_band = PriceBand(
        min_paise_per_qtl=lot.price_min_paise_per_qtl or 0,
        mid_paise_per_qtl=lot.price_mid_paise_per_qtl or 0,
        max_paise_per_qtl=lot.price_max_paise_per_qtl or 0,
    )

    # Compute sale window
    lot_lat = lot.lat or 28.6139
    lot_lng = lot.lng or 77.2090

    nearest_mandi = await _find_nearest_mandi(db, lot_lat, lot_lng)
    mandi_name = nearest_mandi.name if nearest_mandi else "Azadpur"
    mandi_lat = nearest_mandi.lat if nearest_mandi else 28.7041
    mandi_lng = nearest_mandi.lng if nearest_mandi else 77.1025

    distance_km = haversine_km(lot_lat, lot_lng, mandi_lat, mandi_lng)

    try:
        window_result = compute_sale_window(
            crop=lot.crop,
            mandi=mandi_name,
            quantity_kg=lot.quantity_kg,
            current_price_mid_paise=lot.price_mid_paise_per_qtl or 200000,
            distance_km=distance_km,
        )
    except Exception:
        window_result = {
            "recommendation": "NO_ADVICE",
            "reason": "Unable to compute sale window at this time."
        }

    # Convert hold_days to hold_until_date
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


async def get_lot_matches(db: AsyncSession, user: User, lot_id: int) -> LotMatchesResponse:
    """Find matching buyer demands for a lot."""
    result = await db.execute(select(Lot).where(Lot.id == lot_id))
    lot = result.scalar_one_or_none()

    if lot is None or lot.farmer_id != user.id:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Lot not found")

    # Get all demands matching this crop
    demand_result = await db.execute(select(BuyerDemand).where(BuyerDemand.crop == lot.crop))
    demands = demand_result.scalars().all()

    # Run matching engine
    matches = match_demands_for_lot(demands, lot)

    # Build response
    match_results = []
    for match in matches:
        demand = match["demand"]
        # Get buyer name
        buyer_result = await db.execute(select(User).where(User.id == demand.buyer_id))
        buyer = buyer_result.scalar_one_or_none()

        distance_km = None
        if lot.lat and lot.lng and demand.lat and demand.lng:
            distance_km = round(haversine_km(lot.lat, lot.lng, demand.lat, demand.lng), 1)

        match_results.append(MatchResult(
            buyer_demand_id=demand.id,
            buyer_name=buyer.name if buyer else None,
            crop=demand.crop,
            desired_qty_kg=demand.desired_qty_kg,
            max_price_paise_per_qtl=demand.max_price_paise_per_qtl,
            distance_km=distance_km,
            match_score=match["match_score"],
        ))

    return LotMatchesResponse(lot_id=lot.id, matches=match_results)
