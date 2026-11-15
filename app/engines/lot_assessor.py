"""Lot assessment — Template Method Pattern.

Owner: Pranay (Lots & Grading LLD §4, Pattern 2).

`BaseLotAssessor.assess_lot()` fixes the order of the four steps:

    1. validate inputs
    2. run the crop-specific grading        <- the only step subclasses change
    3. compute the assessed value (integer paise)
    4. return the grade + advice

Subclasses fill in step 2 only. They cannot skip validation or change how
money is calculated.
"""
from abc import ABC, abstractmethod
from dataclasses import dataclass, field
from typing import Any, Optional

from app.engines.strategies.grading_strategy import GradeResult, IGradingStrategy


class GradingInputError(ValueError):
    """Bad grading parameters (negative, above 100%, or missing)."""


@dataclass
class AssessmentResult:
    lot_id: Optional[int]
    grade: str
    assessed_multiplier: float
    strategy: str
    # Expected price per quintal after the grade discount.
    assessed_price_paise_per_qtl: Optional[int]
    # Whole-lot value = assessed price per quintal x quantity in quintals.
    assessed_value_paise: Optional[int]
    advice: list[str] = field(default_factory=list)


class BaseLotAssessor(ABC):

    def assess_lot(self, lot: Any, raw_params: dict) -> AssessmentResult:
        """Template method: the fixed skeleton of every lot assessment."""
        params = self._validate_inputs(raw_params)
        grade_result = self._apply_grading_strategy(params)
        price_per_qtl = self._calculate_assessed_value(
            getattr(lot, "expected_price_paise", None), grade_result.multiplier_bps
        )
        quantity_qtl = getattr(lot, "quantity_qtl", None)
        total = price_per_qtl * quantity_qtl if price_per_qtl is not None and quantity_qtl else None
        return AssessmentResult(
            lot_id=getattr(lot, "id", None),
            grade=grade_result.grade,
            assessed_multiplier=grade_result.assessed_multiplier,
            strategy=self._strategy_name(),
            assessed_price_paise_per_qtl=price_per_qtl,
            assessed_value_paise=total,
            advice=list(grade_result.tips),
        )

    # Step 1 — shared by every subclass.
    def _validate_inputs(self, params: dict) -> dict:
        clean: dict = {}
        for key, value in params.items():
            if value is None:
                continue  # optional parameter not sent
            if isinstance(value, bool) or not isinstance(value, (int, float)):
                raise GradingInputError(f"{key} must be a number.")
            if value < 0:
                raise GradingInputError("Grading parameters cannot be negative.")
            if key.endswith("_pct") and value > 100:
                raise GradingInputError(f"{key} is a percentage and cannot be above 100.")
            clean[key] = value
        missing = [p for p in self._required_params() if p not in clean]
        if missing:
            raise GradingInputError(f"Missing required parameters: {', '.join(missing)}")
        return clean

    # Step 2 — the hook subclasses must provide.
    @abstractmethod
    def _apply_grading_strategy(self, params: dict) -> GradeResult: ...

    def _required_params(self) -> tuple[str, ...]:
        return ()

    def _strategy_name(self) -> str:
        return "unknown"

    # Step 3 — integer basis-point math, never float, so paise stay exact.
    def _calculate_assessed_value(self, base_price_paise: Optional[int], multiplier_bps: int) -> Optional[int]:
        if base_price_paise is None:
            return None
        return base_price_paise * multiplier_bps // 10_000


class StrategyLotAssessor(BaseLotAssessor):
    """The concrete assessor: step 2 delegates to an injected grading strategy."""

    def __init__(self, strategy: IGradingStrategy):
        self.strategy = strategy

    def _apply_grading_strategy(self, params: dict) -> GradeResult:
        return self.strategy.evaluate(params)

    def _required_params(self) -> tuple[str, ...]:
        return self.strategy.required_params

    def _strategy_name(self) -> str:
        return self.strategy.name
