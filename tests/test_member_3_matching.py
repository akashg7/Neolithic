"""
Automated Pytest Suite for Member 3 (Akash) — Marketplace Optimization & Matching Engine.
Tests Strategy Pattern, Builder Pattern, Haversine Spatial Pruning, and Multi-Lot Aggregation.
"""

import pytest
from app.engines.strategies.matching_strategy import (
    IMatchingStrategy,
    GreedyHaversineStrategy,
    FastClearanceStrategy,
    PriceOptimizedStrategy,
)
from app.engines.matching_engine import MatchingEngine, matching_engine
from app.domain.builders.match_result_builder import MatchResultBuilder
from app.schemas.logistics import TransportEstimateReq
from app.routers.logistics import estimate_transport_cost


# Override DB setup so unit tests run in-memory with zero external DB dependencies
@pytest.fixture(autouse=True)
def setup_db():
    yield


class MockLot:
    """Mock domain object for a farmer produce lot."""
    def __init__(
        self,
        id: int,
        commodity_id: int,
        quality_grade: str,
        expected_price_paise: int,
        quantity_qtl: int,
        lat: float,
        lng: float,
        status: str = "available"
    ):
        self.id = id
        self.commodity_id = commodity_id
        self.quality_grade = quality_grade
        self.grade = quality_grade
        self.expected_price_paise = expected_price_paise
        self.quantity_qtl = quantity_qtl
        self.qty_kg = quantity_qtl * 100
        self.lat = lat
        self.lng = lng
        self.status = status


class MockDemand:
    """Mock domain object for a bulk buyer demand."""
    def __init__(
        self,
        id: int,
        commodity_id: int,
        desired_grade: str,
        max_price_paise: int,
        quantity_qtl: int,
        lat: float,
        lng: float
    ):
        self.id = id
        self.commodity_id = commodity_id
        self.desired_grade = desired_grade
        self.max_price_paise_per_qtl = max_price_paise
        self.expected_price_paise = max_price_paise
        self.quantity_qtl = quantity_qtl
        self.qty_kg = quantity_qtl * 100
        self.lat = lat
        self.lng = lng


# ─────────────────────────────────────────────────────────────────────────────
# 1. Strategy Pattern Tests (GoF Behavioral Pattern)
# ─────────────────────────────────────────────────────────────────────────────

def test_strategy_interface_cannot_be_instantiated():
    """Verify that IMatchingStrategy is an abstract base class enforcing the contract."""
    with pytest.raises(TypeError):
        IMatchingStrategy()  # type: ignore


def test_greedy_haversine_single_lot_full_fill():
    """Verify single nearby lot with adequate quantity yields a SINGLE match row."""
    # Buyer in Nashik needing 50 quintals of Grade A Onion at ₹2,500/qtl
    demand = MockDemand(1, commodity_id=1, desired_grade="A", max_price_paise=250000, quantity_qtl=50, lat=19.99, lng=73.78)
    # Farmer nearby in Lasalgaon with 60 quintals of Grade A Onion at ₹2,400/qtl
    large_lot = MockLot(101, commodity_id=1, quality_grade="A", expected_price_paise=240000, quantity_qtl=60, lat=20.14, lng=74.23)

    strategy = GreedyHaversineStrategy()
    result = strategy.match(demand, [large_lot])

    assert "matches" in result
    assert len(result["matches"]) == 1
    match = result["matches"][0]
    assert match["kind"] == "SINGLE"
    assert match["fill_bps"] == 10000  # 100% full fill
    assert match["total_qty_kg"] == 5000  # 50 qtl = 5000 kg
    assert match["lots"][0]["lot_id"] == "101"
    assert match["lots"][0]["qty_allocated_kg"] == 5000


def test_greedy_haversine_combination_aggregation():
    """Verify multiple smaller fragmented farmer lots are aggregated into a COMBINATION match."""
    # Buyer needing 100 quintals (10,000 kg)
    demand = MockDemand(2, commodity_id=1, desired_grade="A", max_price_paise=250000, quantity_qtl=100, lat=19.99, lng=73.78)
    
    # 3 Smallholder farmers: 40 qtl, 40 qtl, 30 qtl
    lot1 = MockLot(1, commodity_id=1, quality_grade="A", expected_price_paise=240000, quantity_qtl=40, lat=20.02, lng=73.85)
    lot2 = MockLot(2, commodity_id=1, quality_grade="A", expected_price_paise=242000, quantity_qtl=40, lat=20.05, lng=73.90)
    lot3 = MockLot(3, commodity_id=1, quality_grade="B", expected_price_paise=230000, quantity_qtl=30, lat=20.10, lng=73.95)

    strategy = GreedyHaversineStrategy()
    result = strategy.match(demand, [lot1, lot2, lot3])

    assert len(result["matches"]) == 1
    match = result["matches"][0]
    assert match["kind"] == "COMBINATION"
    assert match["fill_bps"] == 10000
    assert match["total_qty_kg"] == 10000  # 4000 + 4000 + 2000 allocated
    assert len(match["lots"]) == 3
    assert match["lots"][0]["qty_allocated_kg"] == 4000
    assert match["lots"][1]["qty_allocated_kg"] == 4000
    assert match["lots"][2]["qty_allocated_kg"] == 2000


def test_greedy_haversine_disqualifies_lots_beyond_500km():
    """Verify candidate lots beyond the 500 km radius threshold return -1.0 score and are pruned."""
    demand = MockDemand(3, commodity_id=1, desired_grade="A", max_price_paise=250000, quantity_qtl=50, lat=19.99, lng=73.78) # Nashik
    far_lot = MockLot(999, commodity_id=1, quality_grade="A", expected_price_paise=200000, quantity_qtl=100, lat=28.61, lng=77.20) # Delhi (~1000 km)

    strategy = GreedyHaversineStrategy()
    score = strategy.score_lot(far_lot, demand)
    assert score == -1.0

    result = strategy.match(demand, [far_lot])
    assert result["matches"] == []


def test_fast_clearance_strategy_prioritizes_proximity():
    """Verify FastClearanceStrategy scores close lots significantly higher than distant lots."""
    demand = MockDemand(4, commodity_id=1, desired_grade="A", max_price_paise=250000, quantity_qtl=50, lat=19.99, lng=73.78)
    close_lot = MockLot(10, commodity_id=1, quality_grade="B", expected_price_paise=250000, quantity_qtl=50, lat=20.05, lng=73.80) # ~10 km
    distant_lot = MockLot(11, commodity_id=1, quality_grade="A", expected_price_paise=220000, quantity_qtl=50, lat=20.80, lng=74.60) # ~120 km

    strategy = FastClearanceStrategy()
    score_close = strategy.score_lot(close_lot, demand)
    score_distant = strategy.score_lot(distant_lot, demand)

    # For fast clearance, proximity is 60% of the score
    assert score_close > score_distant


def test_fast_clearance_stricter_radius_cutoff():
    """Verify FastClearanceStrategy enforces a 150 km cutoff."""
    demand = MockDemand(5, commodity_id=1, desired_grade="A", max_price_paise=250000, quantity_qtl=50, lat=19.99, lng=73.78)
    lot_200km = MockLot(12, commodity_id=1, quality_grade="A", expected_price_paise=200000, quantity_qtl=50, lat=18.52, lng=73.85) # Pune (~200 km)

    strategy = FastClearanceStrategy()
    score = strategy.score_lot(lot_200km, demand)
    assert score == -1.0


def test_price_optimized_strategy_prioritizes_budget():
    """Verify PriceOptimizedStrategy rewards cheaper produce over proximity."""
    demand = MockDemand(6, commodity_id=1, desired_grade="A", max_price_paise=300000, quantity_qtl=50, lat=19.99, lng=73.78)
    cheap_lot = MockLot(20, commodity_id=1, quality_grade="A", expected_price_paise=200000, quantity_qtl=50, lat=20.50, lng=74.50) # Cheaper
    expensive_close_lot = MockLot(21, commodity_id=1, quality_grade="A", expected_price_paise=295000, quantity_qtl=50, lat=20.01, lng=73.79) # Expensive

    strategy = PriceOptimizedStrategy()
    score_cheap = strategy.score_lot(cheap_lot, demand)
    score_expensive = strategy.score_lot(expensive_close_lot, demand)

    assert score_cheap > score_expensive


def test_matching_engine_dynamic_strategy_swapping():
    """Verify MatchingEngine context allows swapping strategies at runtime."""
    engine = MatchingEngine()
    assert isinstance(engine.get_strategy(), GreedyHaversineStrategy)

    fast_strat = FastClearanceStrategy()
    engine.set_strategy(fast_strat)
    assert isinstance(engine.get_strategy(), FastClearanceStrategy)
    assert engine.get_strategy().name == "FAST_CLEARANCE"

    with pytest.raises(TypeError):
        engine.set_strategy("not_a_strategy")  # type: ignore


# ─────────────────────────────────────────────────────────────────────────────
# 2. Builder Pattern Tests (GoF Creational Pattern)
# ─────────────────────────────────────────────────────────────────────────────

def test_builder_pattern_fluent_assembly():
    """Verify MatchResultBuilder step-by-step construction and invariant calculations."""
    builder = MatchResultBuilder(target_qty_kg=5000)

    row = (
        builder.set_kind("COMBINATION")
        .set_grade("A")
        .add_lot(lot_id="101", qty_allocated_kg=2500, score=0.90, distance_km=30.0)
        .add_lot(lot_id="102", qty_allocated_kg=2500, score=0.80, distance_km=40.0)
        .set_explanation("All criteria met.", "सर्व अटी पूर्ण.")
        .build_row()
    )

    assert row["kind"] == "COMBINATION"
    assert row["grade"] == "A"
    assert row["total_qty_kg"] == 5000
    assert row["fill_bps"] == 10000
    assert row["avg_score"] == 850  # Average of 0.90 and 0.80 is 0.85 -> 850
    assert row["distance_km"] == 35.0  # Average of 30 and 40
    assert len(row["lots"]) == 2
    assert row["why_en"] == "All criteria met."


def test_builder_pattern_partial_fill_bps():
    """Verify fill_bps calculation when total allocated quantity is less than target."""
    builder = MatchResultBuilder(target_qty_kg=10000)
    builder.add_lot(lot_id="201", qty_allocated_kg=4000, score=0.85)
    row = builder.build_row()

    assert row["total_qty_kg"] == 4000
    assert row["fill_bps"] == 4000  # 40% = 4000 basis points


# ─────────────────────────────────────────────────────────────────────────────
# 3. Domain Logic & Edge Case Tests
# ─────────────────────────────────────────────────────────────────────────────

def test_matching_engine_ignores_sold_and_cancelled_lots():
    """Verify matching engine skips inactive lots."""
    demand = MockDemand(7, commodity_id=1, desired_grade="A", max_price_paise=250000, quantity_qtl=50, lat=19.99, lng=73.78)
    sold_lot = MockLot(301, commodity_id=1, quality_grade="A", expected_price_paise=240000, quantity_qtl=50, lat=20.02, lng=73.80, status="sold")
    cancelled_lot = MockLot(302, commodity_id=1, quality_grade="A", expected_price_paise=240000, quantity_qtl=50, lat=20.02, lng=73.80, status="cancelled")

    engine = MatchingEngine()
    result = engine.match_lots_for_demand([sold_lot, cancelled_lot], demand)
    assert result["matches"] == []


def test_matching_engine_different_commodity_ignored():
    """Verify candidate lots with a different commodity_id are excluded."""
    demand_onion = MockDemand(8, commodity_id=1, desired_grade="A", max_price_paise=250000, quantity_qtl=50, lat=19.99, lng=73.78)
    lot_soybean = MockLot(401, commodity_id=2, quality_grade="A", expected_price_paise=240000, quantity_qtl=50, lat=20.02, lng=73.80)

    engine = MatchingEngine()
    result = engine.match_lots_for_demand([lot_soybean], demand_onion)
    assert result["matches"] == []


def test_matching_demands_for_single_lot():
    """Verify match_demands_for_lot reverse matching for farmer view."""
    lot = MockLot(501, commodity_id=1, quality_grade="A", expected_price_paise=220000, quantity_qtl=30, lat=20.02, lng=73.80)
    demand1 = MockDemand(10, commodity_id=1, desired_grade="A", max_price_paise=250000, quantity_qtl=50, lat=20.05, lng=73.85)
    demand2 = MockDemand(11, commodity_id=2, desired_grade="A", max_price_paise=250000, quantity_qtl=50, lat=20.05, lng=73.85)

    engine = MatchingEngine()
    result = engine.match_demands_for_lot([demand1, demand2], lot)
    assert len(result["matches"]) == 1
    assert result["matches"][0]["lots"][0]["lot_id"] == "501"


# ─────────────────────────────────────────────────────────────────────────────
# 4. Logistics Transport Cost Estimation Tests
# ─────────────────────────────────────────────────────────────────────────────

@pytest.mark.asyncio
async def test_logistics_transport_cost_estimate():
    """Verify logistics freight cost estimation endpoint based on Haversine distance."""
    # Nashik (20.0, 73.78) to Pune (18.52, 73.85) ~165 km
    req = TransportEstimateReq(
        origin_lat=20.00,
        origin_lng=73.78,
        dest_lat=18.52,
        dest_lng=73.85,
        qty_qtl=50,
        commodity_name="Onion"
    )

    estimate = await estimate_transport_cost(req)

    assert estimate.distance_km > 150.0
    assert estimate.qty_qtl == 50
    assert estimate.base_rate_per_km_paise == 450
    assert estimate.estimated_freight_paise > 0
    assert estimate.estimated_transit_hours > 3.0
    assert "freight transit" in estimate.route_summary
