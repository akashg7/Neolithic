# Member 3: Demand Aggregation & Smart Multi-Lot Matching Engine

> **Assigned Team Member:** Member 3  
> **Core Role:** Marketplace Optimization & Spatial Algorithms Engineer  
> **Execution Priority:** **Step 3 (Executes Third)** — Consumes Member 1's `Buyer` and Member 2's `Lot` pool; Feeds matched bundles to Member 4.

---

## 1. Domain Responsibility & Scope

Member 3 solves the core agricultural challenge of **supply fragmentation**:
1. **Bulk Buyer Demand Management (`app/models/demand.py`, `app/routers/demands.py`)**: Allowing large buyers (e.g. food chains, exporters, retail aggregators) to post procurement demands with quantity, quality, and location parameters.
2. **Greedy Multi-Lot Matching Engine (`app/engines/matching_engine.py`)**: Scoring and bundling multiple fragmented smallholder farmer lots (< 500 km radius) to satisfy large buyer orders.
3. **Spatial Logistics & Cost Routing (`app/models/reference.py`, `app/utils/haversine.py`)**: Calculating accurate road/geodesic distance and transport freight estimates.

---

## 2. Assigned Database Models (4 Tables)

Member 3 owns the following models in [`app/models/`](file:///Users/akashg/Desktop/Agriculture/Neolithic/app/models/):

| Model Name | Table Name | Purpose | Key Attributes & Foreign Keys |
| :--- | :--- | :--- | :--- |
| **`BuyerDemand`** | `buyer_demands` | Bulk procurement order | `id` (PK), `buyer_id` (FK $\to$ `users.id`), `commodity_id`, `target_quantity_qtl`, `max_price_paise`, `desired_grade`, `delivery_location` (Point) |
| **`MandiLocation`** | `mandi_locations` | APMC physical market | `id` (PK), `name` (e.g. Lasalgaon APMC), `district_id`, `latitude`, `longitude`, `geom` (PostGIS Point) |
| **`Warehouse`** | `warehouses` | WDRA storage locations | `id` (PK), `name`, `district_id`, `capacity_mt`, `cold_storage_flag`, `rate_paise_per_qtl_day` |
| **`LogisticsCostRoute`**| `logistics_routes`| Base freight pricing | `id` (PK), `origin_district`, `destination_district`, `base_rate_per_km_paise` |

---

## 3. Assigned REST APIs (Endpoints & Contracts)

Member 3 owns [`app/routers/demands.py`](file:///Users/akashg/Desktop/Agriculture/Neolithic/app/routers/demands.py) and logistics endpoints in [`app/routers/logistics.py`](file:///Users/akashg/Desktop/Agriculture/Neolithic/app/routers/logistics.py):

| Method | Endpoint | Request Payload | Response Schema | Description |
| :--- | :--- | :--- | :--- | :--- |
| `POST` | `/api/v1/demands` | `{"commodity_id": "Onion", "target_quantity_qtl": 100, "max_price_paise": 240000}` | `DemandOut` | Buyer posts procurement requirement |
| `GET` | `/api/v1/demands` | *Headers: Bearer Token (Buyer)* | `List[DemandOut]` | Lists active demands for current buyer |
| `GET` | `/api/v1/demands/{id}/matches` | *Path: demand_id* | `AggregatedMatchResultOut`| Runs matching engine; returns bundled lots satisfying demand |
| `GET` | `/api/v1/ref/mandis` | `?district=Nashik` | `List[MandiOut]` | Fetches APMC mandis with coordinates |
| `POST` | `/api/v1/logistics/estimate` | `{"origin_lat": 20.1, "origin_lng": 74.2, "dest_lat": 18.5, "dest_lng": 73.8, "qty_qtl": 50}` | `TransportEstimateOut` | Returns Haversine distance & estimated freight cost in paise |

---

## 4. GoF Design Patterns Implementation

### Pattern 1: Strategy Pattern (Behavioral)
- **Problem Solved**: Matching criteria vary by business priority:
  - *Standard*: Balanced trade-off between price, quality, and distance.
  - *Perishable Fast Clearance*: Minimize transit distance (< 100 km) to prevent spoilage.
  - *Budget Optimized*: Minimize procurement price per quintal regardless of distance.
- **Implementation**:
  - `IMatchingStrategy` (Interface defining `match(demand, candidate_lots) -> MatchResult`).
  - `GreedyHaversineStrategy` (Weighted scoring: 40% Grade, 30% Price, 30% Distance).
  - `FastClearanceStrategy` (60% Distance, 30% Grade, 10% Price).

```python
# app/engines/strategies/matching_strategy.py
from abc import ABC, abstractmethod
from typing import List
from app.utils.haversine import haversine_distance_km

class IMatchingStrategy(ABC):
    @abstractmethod
    def score_lot(self, demand, lot) -> float: ...

    @abstractmethod
    def match(self, demand, candidate_lots: list) -> list: ...

class GreedyHaversineStrategy(IMatchingStrategy):
    W_GRADE = 0.40
    W_PRICE = 0.30
    W_PROXIMITY = 0.30
    MAX_RADIUS_KM = 500.0

    def score_lot(self, demand, lot) -> float:
        # 1. Grade score
        grade_score = 1.0 if lot.quality_grade == demand.desired_grade else 0.6
        
        # 2. Price competitiveness
        price_diff = demand.max_price_paise - lot.expected_price_paise
        price_score = max(0.0, min(1.0, 0.5 + (price_diff / 50000.0)))
        
        # 3. Proximity score (Haversine distance)
        dist_km = haversine_distance_km(demand.delivery_lat, demand.delivery_lng, lot.lat, lot.lng)
        if dist_km > self.MAX_RADIUS_KM:
            return -1.0  # Disqualify if outside 500 km
        proximity_score = 1.0 - (dist_km / self.MAX_RADIUS_KM)

        return (self.W_GRADE * grade_score) + (self.W_PRICE * price_score) + (self.W_PROXIMITY * proximity_score)

    def match(self, demand, candidate_lots: list) -> list:
        # Score and filter candidate lots
        scored = []
        for lot in candidate_lots:
            score = self.score_lot(demand, lot)
            if score > 0:
                scored.append((score, lot))
        
        # Sort descending by score
        scored.sort(key=lambda x: x[0], reverse=True)

        # Greedily bundle lots until target quantity is satisfied
        selected_lots = []
        current_qty = 0
        for score, lot in scored:
            selected_lots.append(lot)
            current_qty += lot.quantity_qtl
            if current_qty >= demand.target_quantity_qtl:
                break
        return selected_lots
```

### Pattern 2: Builder Pattern (Creational)
- **Problem Solved**: Constructing an `AggregatedMatchResult` requires aggregating multiple lot objects, calculating weighted average prices, computing composite logistics estimates, and checking fulfillment ratios.
- **Implementation**:

```python
# app/domain/builders/match_result_builder.py
class MatchResultBuilder:
    def __init__(self, demand):
        self.demand = demand
        self.lots = []
        self.total_quantity_qtl = 0
        self.total_cost_paise = 0

    def add_lot(self, lot):
        self.lots.append(lot)
        self.total_quantity_qtl += lot.quantity_qtl
        self.total_cost_paise += (lot.quantity_qtl * lot.expected_price_paise)
        return self

    def build(self) -> dict:
        fulfillment_pct = min(100.0, (self.total_quantity_qtl / self.demand.target_quantity_qtl) * 100.0)
        avg_price_paise = int(self.total_cost_paise / self.total_quantity_qtl) if self.total_quantity_qtl > 0 else 0
        return {
            "demand_id": self.demand.id,
            "lots_matched": [lot.id for lot in self.lots],
            "total_lots_count": len(self.lots),
            "total_quantity_qtl": self.total_quantity_qtl,
            "fulfillment_pct": round(fulfillment_pct, 2),
            "weighted_avg_price_paise": avg_price_paise
        }
```

---

## 5. SOLID Principles Proof Matrix (Member 3)

1. **Single Responsibility Principle (SRP)**:
   - `DemandRouter` handles client query parsing; `MatchingEngine` handles multi-attribute mathematical optimization; `MatchResultBuilder` formats the composite payload.
2. **Open/Closed Principle (OCP)**:
   - Adding a new matching algorithm (e.g., `OrganicCropMatchingStrategy`) requires implementing `IMatchingStrategy`. No existing matching code is modified.
3. **Liskov Substitution Principle (LSP)**:
   - `GreedyHaversineStrategy` and `FastClearanceStrategy` are interchangeable anywhere `IMatchingStrategy` is called.
4. **Interface Segregation Principle (ISP)**:
   - Distance math is isolated in `app/utils/haversine.py`, keeping the matching algorithm clean from database or GIS network drivers.
5. **Dependency Inversion Principle (DIP)**:
   - `DemandService` depends on `IMatchingStrategy` abstraction rather than a hardcoded greedy routine.

---

## 6. Pytest Automated Test Suite

Save in `tests/test_member_3_matching.py`:

```python
import pytest
from app.engines.strategies.matching_strategy import GreedyHaversineStrategy

class MockLot:
    def __init__(self, id, quality_grade, expected_price_paise, quantity_qtl, lat, lng):
        self.id = id
        self.quality_grade = quality_grade
        self.expected_price_paise = expected_price_paise
        self.quantity_qtl = quantity_qtl
        self.lat = lat
        self.lng = lng

class MockDemand:
    def __init__(self, desired_grade, max_price_paise, target_quantity_qtl, delivery_lat, delivery_lng):
        self.desired_grade = desired_grade
        self.max_price_paise = max_price_paise
        self.target_quantity_qtl = target_quantity_qtl
        self.delivery_lat = delivery_lat
        self.delivery_lng = delivery_lng

def test_greedy_aggregation_fulfills_demand():
    demand = MockDemand("A", 250000, 50, 19.99, 73.78)  # Needs 50 qtl
    lot1 = MockLot(1, "A", 240000, 20, 20.01, 73.80)     # 20 qtl nearby
    lot2 = MockLot(2, "A", 235000, 30, 20.05, 73.85)     # 30 qtl nearby
    lot3 = MockLot(3, "B", 200000, 40, 20.10, 73.90)     # Extra lot

    strategy = GreedyHaversineStrategy()
    matched = strategy.match(demand, [lot1, lot2, lot3])
    
    assert len(matched) == 2
    assert sum(l.quantity_qtl for l in matched) == 50

def test_lots_outside_500km_are_disqualified():
    demand = MockDemand("A", 250000, 50, 19.99, 73.78)
    lot_far = MockLot(99, "A", 200000, 50, 28.61, 77.20) # Delhi (~1000 km away)
    strategy = GreedyHaversineStrategy()
    score = strategy.score_lot(demand, lot_far)
    assert score == -1.0
```

---

## 7. Faculty Viva Defense Guide (Member 3)

* **Faculty Q: "What algorithm do you use to aggregate multiple small farmer lots, and what is its computational complexity?"**
  * *Answer:* *"We use a Greedy Multi-Attribute Knapsack approach. First, we filter and score all $N$ candidate lots within a 500 km radius using our composite scoring function (evaluating Grade, Price, and Haversine distance), which takes $O(N)$ time. Next, we sort candidate lots descending by score in $O(N \log N)$ time. Finally, we greedily accumulate lots into the delivery basket until the buyer's desired quantity is fulfilled in $O(K)$ time (where $K \le N$). Total runtime is $O(N \log N)$, easily executing in sub-5ms for typical mandi regions."*

* **Faculty Q: "Why did you use the Builder pattern for the match result?"**
  * *Answer:* *"An aggregated match is a complex composite object consisting of multiple dynamic lots, weighted average price calculations, total volume fulfillment percentages, and route estimates. Constructing this inside the service creates bloated, error-prone constructors. The `MatchResultBuilder` cleanly encapsulates the step-by-step assembly of the response DTO."*

