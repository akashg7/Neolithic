"""Grades a farmer's lot from measured quality parameters. Owner: Pranay.

Flow for `POST /api/v1/lots/{id}/grade`:
    load lot (404 unless the caller owns it)
    → pick the crop's strategy from the registry
    → BaseLotAssessor template method (validate → grade → value → advice)
    → save the grade on the lot
"""
from fastapi import HTTPException, status

from app.domain import lot_lifecycle
from app.engines.lot_assessor import GradingInputError, StrategyLotAssessor
from app.engines.strategies.grading_strategy import GradingStrategyRegistry
from app.models.user import User
from app.repositories.lot_repository import ICommodityRepository, ILotRepository
from app.schemas.lot import GradeRequest, GradeResultOut


class LotGradingService:
    def __init__(
        self,
        lot_repo: ILotRepository,
        commodity_repo: ICommodityRepository,
        registry: GradingStrategyRegistry,
    ):
        self.lot_repo = lot_repo
        self.commodity_repo = commodity_repo
        self.registry = registry

    async def grade_lot(self, user: User, lot_id: int, payload: GradeRequest) -> GradeResultOut:
        lot = await self.lot_repo.get_by_id(lot_id)
        if lot is None or lot.farmer_id != user.id:
            # 404, not 403: don't confirm someone else's lot exists.
            raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Lot not found")

        if (lot.status or "").lower() != lot_lifecycle.ACTIVE:
            raise HTTPException(
                status_code=status.HTTP_409_CONFLICT,
                detail=f"Only active lots can be graded (this lot is '{lot.status}').",
            )

        commodity_name = await self.commodity_repo.get_name(lot.commodity_id)
        try:
            strategy = self.registry.for_commodity(commodity_name or "")
        except ValueError as exc:
            raise HTTPException(status_code=status.HTTP_422_UNPROCESSABLE_ENTITY, detail=str(exc))

        try:
            result = StrategyLotAssessor(strategy).assess_lot(lot, payload.model_dump())
        except GradingInputError as exc:
            raise HTTPException(status_code=status.HTTP_422_UNPROCESSABLE_ENTITY, detail=str(exc))

        lot.grade = result.grade
        await self.lot_repo.update(lot)

        return GradeResultOut(
            lot_id=str(lot.id),
            commodity=commodity_name,
            strategy=result.strategy,
            grade=result.grade,
            assessed_multiplier=result.assessed_multiplier,
            assessed_price_paise_per_qtl=result.assessed_price_paise_per_qtl,
            assessed_value_paise=result.assessed_value_paise,
            advice=result.advice,
        )
