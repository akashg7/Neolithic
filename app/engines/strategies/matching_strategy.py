"""
Matching Strategy Interface and Concrete Strategies.
Implements the Gang of Four (GoF) Strategy Pattern for lot-demand matching.
Member 3: Akash — Marketplace Optimization & Spatial Algorithms.
"""

from abc import ABC, abstractmethod
from typing import List, Dict, Any, Optional
from app.utils.haversine import haversine_km


def _get_demand_qty_kg(demand) -> int:
    """Helper to extract demand quantity in kg."""
    if hasattr(demand, "qty_kg") and demand.qty_kg is not None:
        return demand.qty_kg
    if hasattr(demand, "quantity_qtl") and demand.quantity_qtl is not None:
        return demand.quantity_qtl * 100
    if isinstance(demand, dict):
        if demand.get("qty_kg") is not None:
            return demand["qty_kg"]
        if demand.get("quantity_qtl") is not None:
            return demand["quantity_qtl"] * 100
    return 1000


def _get_lot_qty_kg(lot) -> int:
    """Helper to extract lot quantity in kg."""
    if hasattr(lot, "qty_kg") and lot.qty_kg is not None:
        return lot.qty_kg
    if hasattr(lot, "quantity_qtl") and lot.quantity_qtl is not None:
        return lot.quantity_qtl * 100
    if isinstance(lot, dict):
        if lot.get("qty_kg") is not None:
            return lot["qty_kg"]
        if lot.get("quantity_qtl") is not None:
            return lot["quantity_qtl"] * 100
    return 1000


def _get_demand_max_price(demand) -> Optional[int]:
    """Helper to extract demand maximum budget price in paise."""
    if hasattr(demand, "max_price_paise_per_qtl") and demand.max_price_paise_per_qtl is not None:
        return demand.max_price_paise_per_qtl
    if hasattr(demand, "expected_price_paise") and demand.expected_price_paise is not None:
        return demand.expected_price_paise
    if isinstance(demand, dict):
        return demand.get("max_price_paise_per_qtl") or demand.get("expected_price_paise")
    return None


def _get_lot_mid_price(lot) -> Optional[int]:
    """Helper to extract lot asking price in paise."""
    if hasattr(lot, "price_mid_paise_per_qtl") and lot.price_mid_paise_per_qtl is not None:
        return lot.price_mid_paise_per_qtl
    if hasattr(lot, "expected_price_paise") and lot.expected_price_paise is not None:
        return lot.expected_price_paise
    if isinstance(lot, dict):
        return lot.get("price_mid_paise_per_qtl") or lot.get("expected_price_paise")
    return None


def _get_attribute(obj, attr_name: str, default=None):
    """Safely get attribute whether object is dict or class instance."""
    if isinstance(obj, dict):
        return obj.get(attr_name, default)
    return getattr(obj, attr_name, default)


class IMatchingStrategy(ABC):
    """
    Abstract Strategy Interface for matching candidate lots against buyer demands.
    Allows swappable matching algorithms without modifying the MatchingEngine context.
    """

    @property
    @abstractmethod
    def name(self) -> str:
        """Name of the matching strategy."""
        pass

    @property
    @abstractmethod
    def max_radius_km(self) -> float:
        """Maximum allowable geographic distance for candidate lots."""
        pass

    @abstractmethod
    def score_lot(self, lot: Any, demand: Any) -> float:
        """
        Calculate compatibility score between a single lot and demand.
        Returns a float between 0.0 and 1.0 (or -1.0 if disqualified).
        """
        pass

    @abstractmethod
    def match(self, demand: Any, candidate_lots: List[Any]) -> Dict[str, Any]:
        """
        Execute matching algorithm to bundle lots fulfilling demand.
        Returns dictionary formatted as {"matches": [MatchRow, ...]}.
        """
        pass


class GreedyHaversineStrategy(IMatchingStrategy):
    """
    Default Balanced Strategy:
    - Balanced weighting: 40% Grade, 30% Price, 30% Proximity.
    - Haversine distance threshold: 500 km radius.
    - Employs greedy multi-lot aggregation to fulfill large buyer orders.
    """

    name: str = "GREEDY_HAVERSINE"
    max_radius_km: float = 500.0

    W_GRADE: float = 0.40
    W_PRICE: float = 0.30
    W_PROXIMITY: float = 0.30

    def score_lot(self, lot: Any, demand: Any) -> float:
        grade_order = {"A": 3, "B": 2, "C": 1, None: 0}
        desired_grade = _get_attribute(demand, "desired_grade")
        lot_grade = _get_attribute(lot, "grade") or _get_attribute(lot, "quality_grade")

        # 1. Grade score (0.0 - 1.0)
        if lot_grade == desired_grade:
            grade_score = 1.0
        elif grade_order.get(lot_grade, 0) > grade_order.get(desired_grade, 0):
            grade_score = 0.85  # Higher grade than required
        elif lot_grade is not None and desired_grade is not None:
            grade_score = 0.40  # Lower grade than required
        else:
            grade_score = 0.60  # Default neutral

        # 2. Proximity score via Haversine distance (0.0 - 1.0)
        lot_lat = _get_attribute(lot, "lat")
        lot_lng = _get_attribute(lot, "lng")
        demand_lat = _get_attribute(demand, "lat")
        demand_lng = _get_attribute(demand, "lng")

        if (
            lot_lat is not None
            and lot_lng is not None
            and demand_lat is not None
            and demand_lng is not None
        ):
            dist_km = haversine_km(lot_lat, lot_lng, demand_lat, demand_lng)
            if dist_km > self.max_radius_km:
                return -1.0  # Disqualified: outside operational radius
            proximity_score = max(0.0, 1.0 - (dist_km / self.max_radius_km))
        else:
            proximity_score = 0.50

        # 3. Price fit (0.0 - 1.0)
        max_p = _get_demand_max_price(demand)
        mid_p = _get_lot_mid_price(lot)

        if max_p and mid_p:
            if mid_p <= max_p:
                price_score = 1.0
            else:
                overshoot = (mid_p - max_p) / max_p
                price_score = max(0.0, 1.0 - overshoot)
        else:
            price_score = 0.50

        return (
            (self.W_GRADE * grade_score)
            + (self.W_PROXIMITY * proximity_score)
            + (self.W_PRICE * price_score)
        )

    def match(self, demand: Any, candidate_lots: List[Any]) -> Dict[str, Any]:
        demand_commodity = _get_attribute(demand, "commodity_id")
        d_qty = _get_demand_qty_kg(demand)

        # Filter by commodity and calculate scores
        scored: List[tuple[Any, float]] = []
        for lot in candidate_lots:
            lot_comm = _get_attribute(lot, "commodity_id")
            if lot_comm != demand_commodity:
                continue
            status = _get_attribute(lot, "status")
            if status in ("sold", "cancelled"):
                continue

            score = self.score_lot(lot, demand)
            if score >= 0.0:
                scored.append((lot, score))

        # Sort candidate lots descending by composite score
        scored.sort(key=lambda x: -x[1])

        if not scored:
            return {"matches": []}

        best_lot, best_score = scored[0]
        best_lot_qty = _get_lot_qty_kg(best_lot)
        matches = []

        # If best single lot fulfills the full demand quantity
        if best_lot_qty >= d_qty:
            lot_id = str(_get_attribute(best_lot, "id"))
            grade = _get_attribute(best_lot, "grade") or _get_attribute(best_lot, "quality_grade")
            if grade not in ("A", "B", "C"):
                grade = "B"
            
            lot_lat = _get_attribute(best_lot, "lat")
            lot_lng = _get_attribute(best_lot, "lng")
            dem_lat = _get_attribute(demand, "lat")
            dem_lng = _get_attribute(demand, "lng")
            distance = 45.0
            if lot_lat and lot_lng and dem_lat and dem_lng:
                distance = round(haversine_km(lot_lat, lot_lng, dem_lat, dem_lng), 1)

            matches.append({
                "kind": "SINGLE",
                "lots": [{"lot_id": lot_id, "qty_allocated_kg": d_qty}],
                "total_qty_kg": d_qty,
                "fill_bps": 10000,
                "avg_score": int(best_score * 1000),
                "grade": grade,
                "distance_km": distance,
                "score": round(best_score, 3),
                "why_mr": "जवळचे अंतर, पूर्ण ऑर्डर एकाच शेतकर्‍याकडून.",
                "why_en": "Close distance, fills full order from a single farmer."
            })
        else:
            # Combination match aggregating multiple smaller lots
            combo_lots = []
            combo_qty = 0
            sum_score = 0.0
            total_dist = 0.0
            valid_dist_count = 0

            for lot, score in scored:
                lot_qty = _get_lot_qty_kg(lot)
                alloc = min(lot_qty, d_qty - combo_qty)
                lot_id = str(_get_attribute(lot, "id"))
                combo_lots.append({"lot_id": lot_id, "qty_allocated_kg": alloc})
                combo_qty += alloc
                sum_score += score

                lot_lat = _get_attribute(lot, "lat")
                lot_lng = _get_attribute(lot, "lng")
                dem_lat = _get_attribute(demand, "lat")
                dem_lng = _get_attribute(demand, "lng")
                if lot_lat and lot_lng and dem_lat and dem_lng:
                    total_dist += haversine_km(lot_lat, lot_lng, dem_lat, dem_lng)
                    valid_dist_count += 1

                if combo_qty >= d_qty:
                    break

            if combo_lots:
                fill_bps = int((combo_qty / d_qty) * 10000) if d_qty > 0 else 0
                avg_score = round(sum_score / len(combo_lots), 3)
                avg_dist = round(total_dist / valid_dist_count, 1) if valid_dist_count > 0 else 50.0

                matches.append({
                    "kind": "COMBINATION",
                    "lots": combo_lots,
                    "total_qty_kg": combo_qty,
                    "fill_bps": fill_bps,
                    "avg_score": int(avg_score * 1000),
                    "grade": "B",
                    "distance_km": avg_dist,
                    "score": avg_score,
                    "why_mr": f"ऑर्डर पूर्ण करण्यासाठी {len(combo_lots)} शेतकर्‍यांची एकत्र खरेदी.",
                    "why_en": f"Fills the order using {len(combo_lots)} aggregated farmer lots."
                })

        return {"matches": matches}


class FastClearanceStrategy(IMatchingStrategy):
    """
    Perishable & Fast-Clearance Strategy:
    - Prioritizes proximity heavily (60% Proximity, 30% Grade, 10% Price).
    - Stricter maximum radius cutoff: 150 km.
    - Designed for highly perishable produce (e.g. Tomato, Spinach, Strawberry)
      to minimize transit time and reduce harvest spoil rates.
    """

    name: str = "FAST_CLEARANCE"
    max_radius_km: float = 150.0

    W_PROXIMITY: float = 0.60
    W_GRADE: float = 0.30
    W_PRICE: float = 0.10

    def score_lot(self, lot: Any, demand: Any) -> float:
        lot_lat = _get_attribute(lot, "lat")
        lot_lng = _get_attribute(lot, "lng")
        demand_lat = _get_attribute(demand, "lat")
        demand_lng = _get_attribute(demand, "lng")

        # Proximity is the primary gating criterion
        if (
            lot_lat is not None
            and lot_lng is not None
            and demand_lat is not None
            and demand_lng is not None
        ):
            dist_km = haversine_km(lot_lat, lot_lng, demand_lat, demand_lng)
            if dist_km > self.max_radius_km:
                return -1.0  # Outside urgent radius
            proximity_score = max(0.0, 1.0 - (dist_km / self.max_radius_km))
        else:
            proximity_score = 0.30

        # Grade score
        grade_order = {"A": 3, "B": 2, "C": 1, None: 0}
        desired_grade = _get_attribute(demand, "desired_grade")
        lot_grade = _get_attribute(lot, "grade") or _get_attribute(lot, "quality_grade")
        grade_score = 1.0 if lot_grade == desired_grade else 0.70

        # Price score
        max_p = _get_demand_max_price(demand)
        mid_p = _get_lot_mid_price(lot)
        price_score = 1.0 if (max_p and mid_p and mid_p <= max_p) else 0.50

        return (
            (self.W_PROXIMITY * proximity_score)
            + (self.W_GRADE * grade_score)
            + (self.W_PRICE * price_score)
        )

    def match(self, demand: Any, candidate_lots: List[Any]) -> Dict[str, Any]:
        # Delegate to greedy bundle using FastClearance weights
        helper = GreedyHaversineStrategy()
        # Override scoring function with FastClearance logic
        demand_commodity = _get_attribute(demand, "commodity_id")
        d_qty = _get_demand_qty_kg(demand)

        scored = []
        for lot in candidate_lots:
            if _get_attribute(lot, "commodity_id") != demand_commodity:
                continue
            if _get_attribute(lot, "status") in ("sold", "cancelled"):
                continue
            score = self.score_lot(lot, demand)
            if score >= 0.0:
                scored.append((lot, score))

        scored.sort(key=lambda x: -x[1])
        if not scored:
            return {"matches": []}

        # Pack greedy combination
        combo_lots = []
        combo_qty = 0
        sum_score = 0.0
        for lot, score in scored:
            lot_qty = _get_lot_qty_kg(lot)
            alloc = min(lot_qty, d_qty - combo_qty)
            combo_lots.append({"lot_id": str(_get_attribute(lot, "id")), "qty_allocated_kg": alloc})
            combo_qty += alloc
            sum_score += score
            if combo_qty >= d_qty:
                break

        fill_bps = int((combo_qty / d_qty) * 10000) if d_qty > 0 else 0
        avg_score = round(sum_score / len(combo_lots), 3)

        return {
            "matches": [{
                "kind": "COMBINATION" if len(combo_lots) > 1 else "SINGLE",
                "lots": combo_lots,
                "total_qty_kg": combo_qty,
                "fill_bps": fill_bps,
                "avg_score": int(avg_score * 1000),
                "grade": "A",
                "distance_km": 25.0,
                "score": avg_score,
                "why_mr": "जलद वाहतुकीसाठी सर्वात जवळच्या शेतांकडून खरेदी (कमी नासाडी).",
                "why_en": "Fast clearance: matched from closest farms to minimize spoilage."
            }]
        }


class PriceOptimizedStrategy(IMatchingStrategy):
    """
    Budget-Sensitive / Price-Optimized Strategy:
    - Prioritizes lowest cost per quintal (60% Price, 20% Grade, 20% Proximity).
    - Allows wider search radius up to 500 km.
    - Designed for large commercial food processors seeking lowest procurement cost.
    """

    name: str = "PRICE_OPTIMIZED"
    max_radius_km: float = 500.0

    W_PRICE: float = 0.60
    W_GRADE: float = 0.20
    W_PROXIMITY: float = 0.20

    def score_lot(self, lot: Any, demand: Any) -> float:
        max_p = _get_demand_max_price(demand)
        mid_p = _get_lot_mid_price(lot)

        # 1. Price Score: Significant reward for being cheaper than max price
        if max_p and mid_p:
            if mid_p <= max_p:
                savings_pct = (max_p - mid_p) / max_p
                price_score = min(1.0, 0.70 + (savings_pct * 0.60))
            else:
                overshoot = (mid_p - max_p) / max_p
                price_score = max(0.0, 0.70 - (overshoot * 2.0))
        else:
            price_score = 0.50

        # 2. Grade
        desired_grade = _get_attribute(demand, "desired_grade")
        lot_grade = _get_attribute(lot, "grade") or _get_attribute(lot, "quality_grade")
        grade_score = 1.0 if lot_grade == desired_grade else 0.60

        # 3. Proximity
        lot_lat = _get_attribute(lot, "lat")
        lot_lng = _get_attribute(lot, "lng")
        dem_lat = _get_attribute(demand, "lat")
        dem_lng = _get_attribute(demand, "lng")
        if lot_lat and lot_lng and dem_lat and dem_lng:
            dist = haversine_km(lot_lat, lot_lng, dem_lat, dem_lng)
            if dist > self.max_radius_km:
                return -1.0
            prox_score = max(0.0, 1.0 - (dist / self.max_radius_km))
        else:
            prox_score = 0.50

        return (
            (self.W_PRICE * price_score)
            + (self.W_GRADE * grade_score)
            + (self.W_PROXIMITY * prox_score)
        )

    def match(self, demand: Any, candidate_lots: List[Any]) -> Dict[str, Any]:
        d_qty = _get_demand_qty_kg(demand)
        demand_comm = _get_attribute(demand, "commodity_id")

        scored = []
        for lot in candidate_lots:
            if _get_attribute(lot, "commodity_id") != demand_comm:
                continue
            if _get_attribute(lot, "status") in ("sold", "cancelled"):
                continue
            score = self.score_lot(lot, demand)
            if score >= 0.0:
                scored.append((lot, score))

        scored.sort(key=lambda x: -x[1])
        if not scored:
            return {"matches": []}

        combo_lots = []
        combo_qty = 0
        sum_score = 0.0
        for lot, score in scored:
            lot_qty = _get_lot_qty_kg(lot)
            alloc = min(lot_qty, d_qty - combo_qty)
            combo_lots.append({"lot_id": str(_get_attribute(lot, "id")), "qty_allocated_kg": alloc})
            combo_qty += alloc
            sum_score += score
            if combo_qty >= d_qty:
                break

        fill_bps = int((combo_qty / d_qty) * 10000) if d_qty > 0 else 0
        avg_score = round(sum_score / len(combo_lots), 3)

        return {
            "matches": [{
                "kind": "COMBINATION" if len(combo_lots) > 1 else "SINGLE",
                "lots": combo_lots,
                "total_qty_kg": combo_qty,
                "fill_bps": fill_bps,
                "avg_score": int(avg_score * 1000),
                "grade": "B",
                "distance_km": 80.0,
                "score": avg_score,
                "why_mr": "किफायतशीर दर: खरेदीदारासाठी कमाल नफा आणि बचत.",
                "why_en": "Budget optimized: prioritized lowest price per quintal."
            }]
        }
