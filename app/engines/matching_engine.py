"""
Matching Engine — Strategy Pattern Context & Multi-Lot Matcher.
Member 3: Akash — Marketplace Optimization & Spatial Algorithms.

Applies the Gang of Four (GoF) Strategy Pattern to decouple matching algorithms
from orchestration and API controllers.
"""

from typing import Optional, List, Dict, Any
from app.utils.haversine import haversine_km
from app.engines.strategies.matching_strategy import (
    IMatchingStrategy,
    GreedyHaversineStrategy,
    FastClearanceStrategy,
    PriceOptimizedStrategy,
    _get_demand_qty_kg,
    _get_lot_qty_kg,
    _get_attribute,
)
from app.domain.builders.match_result_builder import MatchResultBuilder

# Expose strategy constants for backward compatibility
W_GRADE = 0.40
W_PROXIMITY = 0.30
W_PRICE = 0.30


class MatchingEngine:
    """
    Context class in the GoF Strategy Pattern.
    Maintains a reference to an IMatchingStrategy and delegates matching
    computations to the active strategy.
    """

    def __init__(self, strategy: Optional[IMatchingStrategy] = None):
        # Default to the balanced GreedyHaversineStrategy
        self._strategy: IMatchingStrategy = strategy or GreedyHaversineStrategy()

    def get_strategy(self) -> IMatchingStrategy:
        """Get the currently configured matching strategy."""
        return self._strategy

    def set_strategy(self, strategy: IMatchingStrategy) -> None:
        """
        Dynamically swap the active strategy at runtime.
        Enables OCP (Open/Closed Principle) and runtime polymorphism.
        """
        if not isinstance(strategy, IMatchingStrategy):
            raise TypeError("Strategy must implement IMatchingStrategy interface.")
        self._strategy = strategy

    def score_lot(self, lot: Any, demand: Any) -> float:
        """Calculate composite compatibility score delegating to active strategy."""
        return self._strategy.score_lot(lot, demand)

    def match_lots_for_demand(self, lots: List[Any], demand: Any) -> Dict[str, Any]:
        """
        Match and aggregate candidate lots for a buyer demand.
        Delegates algorithmic bundling to the active strategy.
        """
        return self._strategy.match(demand, lots)

    def match_demands_for_lot(self, demands: List[Any], lot: Any) -> Dict[str, Any]:
        """
        Find top matching buyer demands for a single farmer lot.
        Uses active strategy's scoring logic.
        """
        lot_qty = _get_lot_qty_kg(lot)
        lot_commodity = _get_attribute(lot, "commodity_id")

        scored = [
            (d, self._strategy.score_lot(lot, d))
            for d in demands
            if _get_attribute(d, "commodity_id") == lot_commodity
        ]
        scored.sort(key=lambda x: -x[1])

        matches = []
        for d, s in scored[:10]:
            if s < 0.0:
                continue
            d_qty = _get_demand_qty_kg(d)
            alloc = min(lot_qty, d_qty)
            fill_bps = int((alloc / d_qty) * 10000) if d_qty > 0 else 0
            lot_grade = _get_attribute(lot, "grade") or _get_attribute(lot, "quality_grade")
            if lot_grade not in ("A", "B", "C"):
                lot_grade = "B"

            matches.append({
                "kind": "SINGLE",
                "lots": [{"lot_id": str(_get_attribute(lot, "id")), "qty_allocated_kg": alloc}],
                "total_qty_kg": alloc,
                "fill_bps": fill_bps,
                "avg_score": int(s * 1000),
                "grade": lot_grade,
                "distance_km": 45.0,
                "score": round(s, 3),
                "why_mr": "उत्तम जुळणी.",
                "why_en": "Good match."
            })

        return {"matches": matches}


# Default global instance
matching_engine = MatchingEngine()


# Module-level functions for 100% backward compatibility
def score_lot(lot, demand) -> float:
    """Backward-compatible functional API delegating to matching_engine."""
    return matching_engine.score_lot(lot, demand)


def match_lots_for_demand(lots: list, demand) -> dict:
    """Backward-compatible functional API delegating to matching_engine."""
    return matching_engine.match_lots_for_demand(lots, demand)


def match_demands_for_lot(demands: list, lot) -> dict:
    """Backward-compatible functional API delegating to matching_engine."""
    return matching_engine.match_demands_for_lot(demands, lot)


__all__ = [
    "IMatchingStrategy",
    "GreedyHaversineStrategy",
    "FastClearanceStrategy",
    "PriceOptimizedStrategy",
    "MatchingEngine",
    "MatchResultBuilder",
    "matching_engine",
    "score_lot",
    "match_lots_for_demand",
    "match_demands_for_lot",
    "W_GRADE",
    "W_PROXIMITY",
    "W_PRICE",
]
