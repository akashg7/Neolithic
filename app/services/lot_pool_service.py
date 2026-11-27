"""FPO lot pooling: merge small farmer lots into one bigger batch lot. Owner: Pranay.

Rules (each one is a test in tests/test_pranay_lots_grading.py):
  * caller must be an FPO admin linked to an FPO (taken from the DB, not the body)
  * at least 2 distinct lots
  * every lot must exist and belong to a farmer of the caller's FPO, else 404
  * all lots must be the same commodity and still "active"
  * batch quantity = sum of quantities
  * batch grade = the lowest member grade; if any member is ungraded, the
    batch is ungraded (we never claim a better grade than we can prove)
  * batch expected price = quantity-weighted average (integer paise), only if
    every member has a price
  * source lots move to "pooled" through the lot lifecycle
"""
from typing import Optional, Sequence

from fastapi import HTTPException, status

from app.domain import lot_lifecycle
from app.models.lot import BatchLotMember, Lot
from app.models.user import User
from app.repositories.fpo_repository import IFpoRepository
from app.repositories.lot_repository import ILotRepository
from app.schemas.lot import BatchLotMemberOut, BatchLotOut

_GRADE_RANK = {"A": 3, "B": 2, "C": 1}


def _not_found(detail: str = "One or more lots not found") -> HTTPException:
    return HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail=detail)


class LotPoolService:
    def __init__(self, lot_repo: ILotRepository, fpo_repo: IFpoRepository):
        self.lot_repo = lot_repo
        self.fpo_repo = fpo_repo

    async def pool(self, user: User, lot_ids: Sequence[int], fpo_id: Optional[int] = None) -> BatchLotOut:
        admin_fpo_id = await self.fpo_repo.get_fpo_id_for_user(user.id)
        if admin_fpo_id is None:
            raise _not_found("FPO not found")
        if fpo_id is not None and fpo_id != admin_fpo_id:
            raise _not_found("FPO not found")

        unique_ids = list(dict.fromkeys(lot_ids))
        if len(unique_ids) != len(lot_ids):
            raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="Duplicate lot IDs")
        if len(unique_ids) < 2:
            raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="Pooling needs at least 2 lots")

        # Row-lock the lots so a second, simultaneous pool request waits here
        # and then sees them as "pooled" instead of pooling them twice.
        lots = list(await self.lot_repo.get_many(unique_ids, lock=True))
        if len(lots) != len(unique_ids):
            raise _not_found()
        farmer_fpos = await self.fpo_repo.get_fpo_ids_for_users([lot.farmer_id for lot in lots])
        for lot in lots:
            if farmer_fpos.get(lot.farmer_id) != admin_fpo_id:
                raise _not_found()

        if len({lot.commodity_id for lot in lots}) > 1:
            raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST,
                                detail="All lots must be the same commodity")
        not_active = [lot.id for lot in lots if not lot_lifecycle.can_transition(lot.status, lot_lifecycle.POOLED)]
        if not_active:
            raise HTTPException(status_code=status.HTTP_409_CONFLICT,
                                detail=f"Only active lots can be pooled. Not active: {not_active}")

        total_qtl = sum(lot.quantity_qtl for lot in lots)
        batch = Lot(
            farmer_id=user.id,           # batch is held by the FPO admin
            fpo_id=admin_fpo_id,
            commodity_id=lots[0].commodity_id,
            quantity_qtl=total_qtl,
            expected_price_paise=self._weighted_price(lots, total_qtl),
            grade=self._batch_grade(lots),
            lat=self._average([lot.lat for lot in lots]),
            lng=self._average([lot.lng for lot in lots]),
            status=lot_lifecycle.ACTIVE,
        )
        batch = await self.lot_repo.create(batch)

        members: list[BatchLotMemberOut] = []
        for lot in lots:
            await self.lot_repo.add_batch_member(BatchLotMember(
                batch_lot_id=batch.id,
                source_lot_id=lot.id,
                quantity_contributed_kg=lot.quantity_qtl * 100,  # column is in kg
            ))
            lot_lifecycle.transition(lot, lot_lifecycle.POOLED)
            await self.lot_repo.update(lot)
            members.append(BatchLotMemberOut(source_lot_id=lot.id, quantity_contributed_qtl=lot.quantity_qtl))

        return BatchLotOut(
            id=batch.id,
            commodity_id=batch.commodity_id,
            quantity_qtl=batch.quantity_qtl,
            grade=batch.grade,
            expected_price_paise=batch.expected_price_paise,
            status=batch.status,
            member_lots=members,
        )

    @staticmethod
    def _batch_grade(lots: Sequence[Lot]) -> Optional[str]:
        grades = [lot.grade for lot in lots]
        if any(g not in _GRADE_RANK for g in grades):
            return None
        return min(grades, key=lambda g: _GRADE_RANK[g])

    @staticmethod
    def _weighted_price(lots: Sequence[Lot], total_qtl: int) -> Optional[int]:
        if total_qtl <= 0 or any(lot.expected_price_paise is None for lot in lots):
            return None
        return sum(lot.expected_price_paise * lot.quantity_qtl for lot in lots) // total_qtl

    @staticmethod
    def _average(values: list) -> Optional[float]:
        present = [v for v in values if v is not None]
        return sum(present) / len(present) if present else None
