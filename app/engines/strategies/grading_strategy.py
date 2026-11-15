"""Crop quality grading — Strategy Pattern.

Owner: Pranay (Lots & Grading LLD §4, Pattern 1).

Every crop family is judged on different physical parameters, so each family
gets its own strategy class behind one small interface, `IGradingStrategy`.
Adding a crop means writing one new class and registering it; existing
strategies are never edited (Open/Closed).

All parameters are percentages (0–100). The thresholds below are simplified
values modelled on AGMARKNET-style grade specifications. They are a prototype
rule set, not the official notified standards.

This sits next to the older `app/engines/grading_engine.grade()` (the six-
question farmer self-assay used by `POST /lots/{id}/assay`). That one is a
quick farmer-facing questionnaire; this one grades measured parameters for
`POST /lots/{id}/grade`. Both stay.
"""
from abc import ABC, abstractmethod
from typing import Any, Dict, Optional

# Grade -> price multiplier in basis points (1 bp = 0.01%). Integer math keeps
# money exact. Same values as app/domain/assessed_value.GRADE_BPS.
GRADE_MULTIPLIER_BPS: Dict[str, int] = {"A": 10_000, "B": 8_500, "C": 7_000}


class GradeResult:
    """What a strategy returns: the grade, its price multiplier and advice."""

    def __init__(self, grade: str, assessed_multiplier: float, tips: list[str]):
        self.grade = grade                              # "A", "B" or "C"
        self.assessed_multiplier = assessed_multiplier  # 1.0, 0.85 or 0.70
        self.tips = tips

    @property
    def multiplier_bps(self) -> int:
        """The multiplier as integer basis points, for money calculations."""
        return GRADE_MULTIPLIER_BPS[self.grade]

    def __repr__(self) -> str:
        return f"GradeResult(grade={self.grade!r}, multiplier={self.assessed_multiplier}, tips={self.tips!r})"


def _result(grade: str, tips: list[str]) -> GradeResult:
    return GradeResult(grade, GRADE_MULTIPLIER_BPS[grade] / 10_000, tips)


class IGradingStrategy(ABC):
    """One crop family's grading rules. Knows nothing about HTTP or the DB."""

    #: Short name, shown in API responses so the farmer knows which rules applied.
    name: str = "base"
    #: Parameters this strategy needs. The assessor checks them before grading.
    required_params: tuple[str, ...] = ()

    @abstractmethod
    def evaluate(self, params: Dict[str, Any]) -> GradeResult: ...


class OnionGradingStrategy(IGradingStrategy):
    """Onion: surface moisture and bulb-size uniformity decide the grade."""

    name = "onion"
    required_params = ("moisture_pct", "size_uniformity_pct")

    def evaluate(self, params: Dict[str, Any]) -> GradeResult:
        moisture = params["moisture_pct"]
        size_uniformity = params["size_uniformity_pct"]
        tips: list[str] = []

        if moisture < 12.0 and size_uniformity >= 85:
            return _result("A", ["Excellent quality. Eligible for premium institutional export."])
        elif moisture <= 15.0 and size_uniformity >= 70:
            if size_uniformity < 85:
                tips.append("Grade into size bins of 45-55mm to reach Grade A pricing.")
            if moisture >= 12.0:
                tips.append("Cure a little longer in shade to bring moisture below 12% for Grade A.")
            return _result("B", tips)
        else:
            if moisture > 15.0:
                tips.append("Cure onions under shade for 48 hours to reduce surface moisture below 15%.")
            if size_uniformity < 70:
                tips.append("Sort out undersized and oversized bulbs so at least 70% are of uniform size.")
            return _result("C", tips)


class PerishableVegetableGradingStrategy(IGradingStrategy):
    """Fresh produce (tomato, potato, chilli, banana): decay is the strict rule.

    Moisture is not a useful signal for fresh vegetables, so these are judged on
    decay/damage, size uniformity and discoloration.
    """

    name = "perishable_vegetable"
    required_params = ("damage_pct", "size_uniformity_pct")

    def evaluate(self, params: Dict[str, Any]) -> GradeResult:
        damage = params["damage_pct"]
        size_uniformity = params["size_uniformity_pct"]
        discoloration = params.get("discoloration_pct", 0.0)
        tips: list[str] = []

        if damage <= 2 and size_uniformity >= 85 and discoloration <= 5:
            return _result("A", ["Fresh, uniform lot. Suitable for retail chains and premium buyers."])
        if damage <= 8 and size_uniformity >= 70 and discoloration <= 15:
            if damage > 2:
                tips.append("Remove bruised or rotting pieces before dispatch to reach Grade A.")
            if size_uniformity < 85:
                tips.append("Sort by size so at least 85% of the lot is uniform for Grade A.")
            if discoloration > 5:
                tips.append("Pick out discoloured pieces; buyers pay more for uniform colour.")
            return _result("B", tips)
        if damage > 8:
            tips.append("Decay is above 8%. Sell quickly, store in shade and separate rotting produce today.")
        if size_uniformity < 70:
            tips.append("Size grading is needed: less than 70% of the lot is uniform.")
        if discoloration > 15:
            tips.append("Heavy discoloration. Harvest at the right maturity and avoid sun exposure after picking.")
        return _result("C", tips)


class OilseedGrainGradingStrategy(IGradingStrategy):
    """Grains, pulses and oilseeds (soybean, wheat, gram, maize ...).

    Moisture and foreign matter (dust, stones, husk) are the two limits that
    buyers check first. Damaged/discoloured grain is an optional third input.
    """

    name = "oilseed_grain"
    required_params = ("moisture_pct", "foreign_matter_pct")

    def evaluate(self, params: Dict[str, Any]) -> GradeResult:
        moisture = params["moisture_pct"]
        foreign = params["foreign_matter_pct"]
        damaged = params.get("damage_pct", 0.0)
        tips: list[str] = []

        if moisture <= 10 and foreign <= 1 and damaged <= 2:
            return _result("A", ["Clean and dry. Meets premium processor and FPO procurement norms."])
        if moisture <= 12 and foreign <= 2 and damaged <= 5:
            if moisture > 10:
                tips.append("Sun-dry for 1-2 more days to bring moisture to 10% or below for Grade A.")
            if foreign > 1:
                tips.append("Sieve or winnow once more to bring foreign matter under 1%.")
            if damaged > 2:
                tips.append("Hand-pick broken and discoloured grains to reach Grade A.")
            return _result("B", tips)
        if moisture > 12:
            tips.append("Moisture is above 12%. Dry on a tarpaulin in the sun to avoid fungus and price cuts.")
        if foreign > 2:
            tips.append("Foreign matter is above 2%. Clean with a sieve or winnower before selling.")
        if damaged > 5:
            tips.append("More than 5% damaged grain. Store in dry, pest-free bags to stop further damage.")
        return _result("C", tips)


class GradingStrategyRegistry:
    """Picks the strategy for a commodity by name (case-insensitive).

    New crop = `registry.register("Cotton", CottonGradingStrategy())`.
    No other code changes.
    """

    def __init__(self, default: Optional[IGradingStrategy] = None):
        self._by_name: Dict[str, IGradingStrategy] = {}
        self._default = default

    def register(self, commodity_name: str, strategy: IGradingStrategy) -> None:
        self._by_name[commodity_name.strip().lower()] = strategy

    def for_commodity(self, commodity_name: str) -> IGradingStrategy:
        strategy = self._by_name.get((commodity_name or "").strip().lower(), self._default)
        if strategy is None:
            raise ValueError(f"No grading rules for commodity {commodity_name!r}")
        return strategy


def build_default_registry() -> GradingStrategyRegistry:
    """Registry covering the 14 seeded Maharashtra commodities."""
    registry = GradingStrategyRegistry()
    registry.register("Onion", OnionGradingStrategy())

    perishable = PerishableVegetableGradingStrategy()
    for name in ("Tomato", "Potato", "Green Chilli", "Banana"):
        registry.register(name, perishable)

    grain = OilseedGrainGradingStrategy()
    # Cotton and turmeric are graded on moisture + trash here as an approximation.
    for name in ("Soyabean", "Soybean", "Wheat", "Bengal Gram", "Maize", "Rice",
                 "Groundnut", "Jowar", "Cotton", "Turmeric"):
        registry.register(name, grain)
    return registry
