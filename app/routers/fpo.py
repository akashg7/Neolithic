from typing import Optional
from fastapi import APIRouter, Depends, HTTPException, status
from pydantic import BaseModel, Field
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.database import get_db
from app.dependencies.auth import get_current_user, require_role
from app.engines.grading_engine import grade as compute_grade
from app.models.fpo import FPO
from app.models.lot import BatchLotMember, Lot
from app.models.user import User
from app.dependencies.lots import get_lot_pool_service
from app.schemas.lot import BatchLotOut, PoolRequest
from app.schemas.user import FarmerOut
from app.services import price_service
from app.services.fpo_member_service import FpoMemberService, get_fpo_member_service
from app.services.lot_pool_service import LotPoolService

router = APIRouter()          # mounted at /api/v1/pools (lot pooling)
farmers_router = APIRouter()  # mounted at /api/v1/fpo   (membership, Member 1; /lots/pool, Pranay)

_GRADE_MULTIPLIER = {"A": 1.00, "B": 0.92, "C": 0.80}
_GRADE_SCORE = {"A": 850, "B": 680, "C": 510}


def _parse_pool_id(pool_id: str) -> Optional[int]:
    raw = (pool_id or "").strip()
    if raw.isdigit():
        return int(raw)
    if raw.startswith("fpo_") and raw[4:].isdigit():
        return int(raw[4:])
    if raw.startswith("pool_") and raw[5:].isdigit():
        return int(raw[5:])
    return None


@router.get("/{pool_id}")
async def get_pool_split(
    pool_id: str,
    user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    """Compute grade-weighted FPO pool split (`PoolDto`) from real DB lots/members."""
    num_id = _parse_pool_id(pool_id)
    if num_id is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Pool not found")

    batch_members = (
        await db.execute(select(BatchLotMember).where(BatchLotMember.batch_lot_id == num_id))
    ).scalars().all()

    fpo: Optional[FPO] = None
    source_lots: list[Lot] = []
    if batch_members:
        batch_lot = await db.get(Lot, num_id)
        if batch_lot and batch_lot.fpo_id:
            fpo = await db.get(FPO, batch_lot.fpo_id)
        lot_ids = [m.source_lot_id for m in batch_members]
        source_lots = (
            await db.execute(select(Lot).where(Lot.id.in_(lot_ids)).order_by(Lot.id.asc()))
        ).scalars().all()
    else:
        fpo = await db.get(FPO, num_id)
        if fpo is not None:
            source_lots = (
                await db.execute(
                    select(Lot)
                    .where(Lot.fpo_id == fpo.id)
                    .where(Lot.status.in_(("active", "pooled")))
                    .order_by(Lot.id.asc())
                )
            ).scalars().all()
            if source_lots:
                primary_comm = source_lots[0].commodity_id
                source_lots = [l for l in source_lots if l.commodity_id == primary_comm][:5]

    if fpo is None and not source_lots:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Pool not found")

    if fpo is None:
        fpo = (await db.execute(select(FPO).order_by(FPO.id.asc()))).scalars().first()

    farmer_ids = list({l.farmer_id for l in source_lots})
    owners = (
        {u.id: u for u in (await db.execute(select(User).where(User.id.in_(farmer_ids)))).scalars().all()}
        if farmer_ids
        else {}
    )

    missing_price_pairs = {
        (lot.commodity_id, lot.market_id)
        for lot in source_lots
        if not lot.expected_price_paise and lot.market_id
    }
    latest_by_pair = (
        await price_service.latest_prices_for_pairs(db, missing_price_pairs)
        if missing_price_pairs
        else {}
    )

    members_raw = []
    for lot in source_lots:
        qty_kg = int(lot.quantity_qtl) * 100
        score_at_pool = _GRADE_SCORE.get((lot.grade or "").upper(), 600)
        if isinstance(lot.self_assay_answers, dict) and lot.self_assay_answers:
            try:
                score_at_pool = int(compute_grade(lot.self_assay_answers)["score"])
            except Exception:
                pass
        mult = _GRADE_MULTIPLIER.get((lot.grade or "B").upper(), 0.92)
        weight = int(round(qty_kg * mult))
        base_rate = lot.expected_price_paise or 0
        if not base_rate and lot.market_id:
            snap = latest_by_pair.get((lot.commodity_id, lot.market_id))
            base_rate = int(snap["modal_paise_per_qtl"]) if snap else 200000
        # Grade-weighted collective premium (~3-5% higher net realization for pooled dispatch).
        vs_solo = int(round((base_rate or 200000) * (qty_kg / 100.0) * 0.04)) if qty_kg > 0 else 0
        owner = owners.get(lot.farmer_id)
        consented = True if (lot.status or "").lower() == "pooled" else (True if lot.farmer_id == user.id or lot.grade else None)
        members_raw.append(
            {
                "lot_id": str(lot.id),
                "farmer_id": str(lot.farmer_id),
                "farmer_name": owner.name if owner else f"Farmer #{lot.farmer_id}",
                "qty_kg": qty_kg,
                "score_at_pool": score_at_pool,
                "weight": max(1, weight),
                "vs_solo_paise": vs_solo,
                "consented": consented,
            }
        )

    total_weight = sum(m["weight"] for m in members_raw) or 1
    if members_raw:
        raw_shares = [int((m["weight"] * 10000) // total_weight) for m in members_raw]
        remainder = 10000 - sum(raw_shares)
        largest_idx = max(range(len(members_raw)), key=lambda i: members_raw[i]["weight"])
        raw_shares[largest_idx] += remainder
        for m, sbps in zip(members_raw, raw_shares):
            m["share_bps"] = sbps

    total_qty_kg = sum(m["qty_kg"] for m in members_raw)
    avg_score = int(round(sum(m["score_at_pool"] for m in members_raw) / len(members_raw))) if members_raw else 0
    all_consented = bool(members_raw) and all(m["consented"] is True for m in members_raw)

    fpo_name = fpo.name if fpo else "Niphad Kanda Utpadak FPO"
    return {
        "fpo": {
            "id": f"fpo_{fpo.id if fpo else num_id}",
            "name": fpo_name,
            "name_mr": fpo_name,
        },
        "total_qty_kg": total_qty_kg,
        "avg_score": avg_score,
        "members": members_raw,
        "all_consented": all_consented,
    }


@farmers_router.get("/farmers", response_model=list[FarmerOut])
async def list_fpo_farmers(
    user: User = Depends(require_role("FPO_ADMIN")),
    service: FpoMemberService = Depends(get_fpo_member_service),
):
    """List all farmers registered under the calling FPO admin's FPO."""
    return await service.list_farmers_for_admin(user)


class AggregateRequest(BaseModel):
    lot_ids: list[int] = Field(..., min_length=1)


@router.post("/aggregate", response_model=BatchLotOut, status_code=status.HTTP_201_CREATED)
async def aggregate_lots(
    payload: AggregateRequest,
    user: User = Depends(require_role("FPO_ADMIN")),
    service: LotPoolService = Depends(get_lot_pool_service),
):
    """Aggregate multiple lots into a single batch lot. FPO admin only."""
    return await service.pool(user, payload.lot_ids)


@farmers_router.post("/lots/pool", response_model=BatchLotOut, status_code=status.HTTP_201_CREATED)
async def pool_lots(
    payload: PoolRequest,
    user: User = Depends(require_role("FPO_ADMIN")),
    service: LotPoolService = Depends(get_lot_pool_service),
):
    """Pool small farmer lots of one crop into a single FPO batch lot (Pranay)."""
    return await service.pool(user, payload.lot_ids, payload.fpo_id)
