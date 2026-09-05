from fastapi import HTTPException, status
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.models.user import User, Farmer
from app.models.lot import Lot, BatchLotMember
from app.models.fpo import FPO
from app.engines.price_engine import price_engine
from app.schemas.lot import BatchLotOut, BatchLotMemberOut

from datetime import datetime


async def aggregate_lots(db: AsyncSession, user: User, lot_ids: list[int]) -> BatchLotOut:
    """
    Aggregate multiple lots into a single batch lot.
    Only FPO admins can do this, and all lots must belong to farmers in their FPO.
    """
    if not lot_ids:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="No lot IDs provided")

    # Get the FPO admin's FPO
    farmer_result = await db.execute(
        select(Farmer).where(Farmer.user_id == user.id)
    )
    admin_farmer = farmer_result.scalar_one_or_none()
    if admin_farmer is None or admin_farmer.fpo_id is None:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="FPO admin must be associated with an FPO"
        )

    fpo_id = admin_farmer.fpo_id

    # Fetch all lots
    lot_result = await db.execute(select(Lot).where(Lot.id.in_(lot_ids)))
    lots = lot_result.scalars().all()

    if len(lots) != len(lot_ids):
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="One or more lots not found")

    # Verify all lots belong to farmers in this FPO
    for lot in lots:
        farmer_check = await db.execute(
            select(Farmer).where(Farmer.user_id == lot.farmer_id, Farmer.fpo_id == fpo_id)
        )
        if farmer_check.scalar_one_or_none() is None:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail=f"Lot {lot.id} does not belong to a farmer in your FPO"
            )

    # Verify all lots have same crop
    crops = set(lot.crop for lot in lots)
    if len(crops) > 1:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=f"All lots must be the same crop. Found: {', '.join(crops)}"
        )

    # Verify all lots are active
    non_active = [lot.id for lot in lots if lot.status != "active"]
    if non_active:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=f"Lots must be active. Non-active lot IDs: {non_active}"
        )

    crop = lots[0].crop
    total_quantity = sum(lot.quantity_kg for lot in lots)

    # Determine grade — use lowest common grade
    grade_order = {"A": 3, "B": 2, "C": 1, None: 0}
    grades = [lot.grade for lot in lots if lot.grade]
    batch_grade = min(grades, key=lambda g: grade_order.get(g, 0)) if grades else None

    # Calculate average lat/lng for the batch
    lats = [lot.lat for lot in lots if lot.lat]
    lngs = [lot.lng for lot in lots if lot.lng]
    avg_lat = sum(lats) / len(lats) if lats else None
    avg_lng = sum(lngs) / len(lngs) if lngs else None

    # Create the batch lot
    batch_lot = Lot(
        farmer_id=user.id,  # Attributed to the FPO admin
        fpo_id=fpo_id,
        crop=crop,
        quantity_kg=total_quantity,
        grade=batch_grade,
        lat=avg_lat,
        lng=avg_lng,
        status="active",
    )

    # Get price prediction for the batch
    try:
        prediction = price_engine.predict("Azadpur", crop, datetime.now().isoformat())
        batch_lot.price_min_paise_per_qtl = prediction["p10_paise"]
        batch_lot.price_mid_paise_per_qtl = prediction["p50_paise"]
        batch_lot.price_max_paise_per_qtl = prediction["p90_paise"]
    except Exception:
        pass

    db.add(batch_lot)
    await db.flush()

    # Create batch_lot_members and update original lots
    member_lots = []
    for lot in lots:
        member = BatchLotMember(
            batch_lot_id=batch_lot.id,
            source_lot_id=lot.id,
            quantity_contributed_kg=lot.quantity_kg,
        )
        db.add(member)
        member_lots.append(BatchLotMemberOut(
            source_lot_id=lot.id,
            quantity_contributed_kg=lot.quantity_kg,
        ))
        lot.status = "aggregated"

    await db.flush()

    return BatchLotOut(
        id=batch_lot.id,
        crop=batch_lot.crop,
        quantity_kg=batch_lot.quantity_kg,
        grade=batch_lot.grade,
        price_min_paise_per_qtl=batch_lot.price_min_paise_per_qtl,
        price_mid_paise_per_qtl=batch_lot.price_mid_paise_per_qtl,
        price_max_paise_per_qtl=batch_lot.price_max_paise_per_qtl,
        status=batch_lot.status,
        member_lots=member_lots,
    )
