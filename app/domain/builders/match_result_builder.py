"""
Match Result Builder — Gang of Four (GoF) Builder Pattern.
Incrementally constructs complex aggregated MatchRow and MatchesRes objects.
Member 3: Akash — Marketplace Optimization & Spatial Algorithms.
"""

from typing import List, Dict, Any, Optional, Literal


class MatchResultBuilder:
    """
    Builder class for constructing complex MatchRow and MatchesRes DTOs.
    Follows Fluent Interface method chaining:
      builder.set_demand(demand).set_kind("COMBINATION").add_lot(...).build()
    """

    def __init__(self, target_qty_kg: int = 1000):
        self.target_qty_kg: int = target_qty_kg
        self.kind: Literal["SINGLE", "COMBINATION"] = "SINGLE"
        self.lots: List[Dict[str, Any]] = []
        self.total_qty_kg: int = 0
        self.grade: Literal["A", "B", "C"] = "B"
        self.total_score: float = 0.0
        self.total_distance: float = 0.0
        self.distance_count: int = 0
        self.why_en: str = "Aggregated matches for demand."
        self.why_mr: str = "मागणीनुसार जुळणारे शेतकरी लॉट्स."

    def reset(self, target_qty_kg: int = 1000) -> "MatchResultBuilder":
        """Reset builder state for a new match assembly."""
        self.__init__(target_qty_kg)
        return self

    def set_kind(self, kind: Literal["SINGLE", "COMBINATION"]) -> "MatchResultBuilder":
        """Set whether match is single farmer or multi-lot aggregation."""
        self.kind = kind
        return self

    def set_grade(self, grade: str) -> "MatchResultBuilder":
        """Set dominant grade of the aggregated batch."""
        if grade in ("A", "B", "C"):
            self.grade = grade
        else:
            self.grade = "B"
        return self

    def add_lot(
        self,
        lot_id: str,
        qty_allocated_kg: int,
        score: float = 0.8,
        distance_km: Optional[float] = None
    ) -> "MatchResultBuilder":
        """Add an allocated lot slice into the aggregated match bundle."""
        self.lots.append({
            "lot_id": str(lot_id),
            "qty_allocated_kg": qty_allocated_kg
        })
        self.total_qty_kg += qty_allocated_kg
        self.total_score += score

        if distance_km is not None and distance_km >= 0:
            self.total_distance += distance_km
            self.distance_count += 1

        if len(self.lots) > 1:
            self.kind = "COMBINATION"

        return self

    def set_explanation(self, why_en: str, why_mr: str) -> "MatchResultBuilder":
        """Set bilingual explainability rationale for farmers and buyers."""
        self.why_en = why_en
        self.why_mr = why_mr
        return self

    def build_row(self) -> Dict[str, Any]:
        """Construct the immutable single MatchRow dictionary."""
        num_lots = len(self.lots)
        if num_lots == 0:
            avg_score = 0.0
            avg_distance = 0.0
        else:
            avg_score = round(self.total_score / num_lots, 3)
            avg_distance = (
                round(self.total_distance / self.distance_count, 1)
                if self.distance_count > 0
                else 45.0
            )

        fill_bps = (
            int((self.total_qty_kg / self.target_qty_kg) * 10000)
            if self.target_qty_kg > 0
            else 10000
        )

        return {
            "kind": self.kind,
            "lots": list(self.lots),
            "total_qty_kg": self.total_qty_kg,
            "fill_bps": min(10000, fill_bps),
            "avg_score": int(avg_score * 1000),
            "grade": self.grade,
            "distance_km": avg_distance,
            "score": avg_score,
            "why_en": self.why_en,
            "why_mr": self.why_mr
        }

    def build_response(self) -> Dict[str, Any]:
        """Construct the complete MatchesRes dictionary containing the match rows."""
        row = self.build_row()
        return {"matches": [row] if self.lots else []}
