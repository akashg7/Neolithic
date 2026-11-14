# Member 2: Produce Lots, Inventory & Crop Quality Grading Engine

> **Assigned Team Member:** Member 2  
> **Core Role:** Domain Inventory & Valuation Engineer  
> **Execution Priority:** **Step 2 (Executes Second)** — Consumes Member 1's `Farmer` & `BaseRepository`; Supplies lots to Member 3.

---

## 1. Domain Responsibility & Scope

Member 2 owns the core supply-side functionality:
1. **Produce Lot Inventory (`app/models/lot.py`, `app/services/lot_service.py`)**: Allowing farmers to create, list, and manage lots with status transitions (`available`, `locked`, `sold`).
2. **Quality Grading Engine (`app/engines/grading_engine.py`)**: Assessing produce parameters (moisture, foreign matter, size uniformity, discoloration) to output standard AGMARKNET Grades (Grade A, B, or C) with personalized improvement advice.
3. **FPO Lot Pooling (`app/services/fpo_service.py`)**: Aggregating small fragmented farmer lots into a single uniform batch.

---

## 2. Assigned Database Models (4 Tables)

Member 2 owns the following models in [`app/models/`](file:///Users/akashg/Desktop/Agriculture/Neolithic/app/models/):

| Model Name | Table Name | Purpose | Key Attributes & Foreign Keys |
| :--- | :--- | :--- | :--- |
| **`Lot`** | `lots` | Core harvest produce batch | `id` (PK), `farmer_id` (FK $\to$ `users.id`), `commodity_id`, `quantity_qtl`, `expected_price_paise`, `quality_grade` (A/B/C), `status` (`available`, `locked`, `sold`) |
| **`BatchLotMember`** | `batch_lot_members` | FPO lot aggregation table | `id` (PK), `fpo_batch_id`, `lot_id` (FK $\to$ `lots.id`), `allocated_quantity_qtl` |
| **`Commodity`** | `commodities` | Reference crop catalog | `id` (PK), `name` (e.g. Onion, Soybean, Cotton), `shelf_life_days`, `grade_standard_json` |
| **`District`** | `districts` | Maharashtra state districts | `id` (PK), `name` (e.g. Nashik, Pune, Ahmednagar), `state` |

---

## 3. Assigned REST APIs (Endpoints & Contracts)

Member 2 owns [`app/routers/lots.py`](file:///Users/akashg/Desktop/Agriculture/Neolithic/app/routers/lots.py):

| Method | Endpoint | Request Payload | Response Schema | Description |
| :--- | :--- | :--- | :--- | :--- |
| `POST` | `/api/v1/lots` | `{"commodity_id": "Onion", "quantity_qtl": 25, "expected_price_paise": 220000}` | `LotOut` | Creates a new produce lot for the farmer |
| `GET` | `/api/v1/lots` | *Headers: Bearer Token (Farmer)* | `List[LotOut]` | Lists all active and historical lots owned by farmer |
| `GET` | `/api/v1/lots/{id}` | *Path: lot_id* | `LotOut` | Fetches details and status of specific lot |
| `POST` | `/api/v1/lots/{id}/grade` | `{"moisture_pct": 12.5, "foreign_matter_pct": 1.2, "size_uniformity_pct": 88}` | `GradeResultOut` | Computes Grade (A/B/C), assessed value, improvement tip |
| `POST` | `/api/v1/fpo/lots/pool` | `{"lot_ids": [101, 102, 103], "fpo_id": 1}` | `FpoBatchOut` | Pools multiple small farmer lots into 1 large FPO lot |

---

## 4. GoF Design Patterns Implementation

### Pattern 1: Strategy Pattern (Behavioral)
- **Problem Solved**: Different commodities have entirely different physical grading parameters. Onions care about size uniformity and rot; Soybeans care about oil content and moisture.
- **Implementation**:
  - `IGradingStrategy` (Interface defining `evaluate(parameters: dict) -> GradeResult`).
  - `PerishableVegetableGradingStrategy` (Applies strict moisture and decay rules).
  - `OilseedGrainGradingStrategy` (Applies foreign matter and moisture limits).

```python
# app/engines/strategies/grading_strategy.py
from abc import ABC, abstractmethod
from typing import Dict, Any

class GradeResult:
    def __init__(self, grade: str, assessed_multiplier: float, tips: list[str]):
        self.grade = grade                      # "A", "B", or "C"
        self.assessed_multiplier = assessed_multiplier  # 1.0, 0.85, or 0.70
        self.tips = tips

class IGradingStrategy(ABC):
    @abstractmethod
    def evaluate(self, params: Dict[str, Any]) -> GradeResult: ...

class OnionGradingStrategy(IGradingStrategy):
    def evaluate(self, params: Dict[str, Any]) -> GradeResult:
        moisture = params.get("moisture_pct", 10.0)
        size_uniformity = params.get("size_uniformity_pct", 80.0)
        tips = []

        if moisture < 12.0 and size_uniformity >= 85:
            return GradeResult("A", 1.0, ["Excellent quality. Eligible for premium institutional export."])
        elif moisture <= 15.0 and size_uniformity >= 70:
            if size_uniformity < 85:
                tips.append("Grade into size bins of 45-55mm to reach Grade A pricing.")
            return GradeResult("B", 0.85, tips)
        else:
            tips.append("Cure onions under shade for 48 hours to reduce surface moisture below 15%.")
            return GradeResult("C", 0.70, tips)
```

### Pattern 2: Template Method Pattern (Behavioral)
- **Problem Solved**: The workflow to assess produce always follows the exact same 4-step sequence: validate input $\to$ run crop-specific grading $\to$ calculate financial assessed value $\to$ generate actionable farmer advice.
- **Implementation**:

```python
# app/engines/lot_assessor.py
from abc import ABC, abstractmethod

class BaseLotAssessor(ABC):
    def assess_lot(self, lot, raw_params: dict) -> dict:
        """Template method defining the skeleton of lot assessment."""
        self._validate_inputs(raw_params)
        grade_result = self._apply_grading_strategy(raw_params)
        assessed_value_paise = self._calculate_assessed_value(lot.expected_price_paise, grade_result.assessed_multiplier)
        return {
            "lot_id": lot.id,
            "grade": grade_result.grade,
            "assessed_value_paise": assessed_value_paise,
            "advice": grade_result.tips
        }

    def _validate_inputs(self, params: dict):
        if any(v < 0 for v in params.values() if isinstance(v, (int, float))):
            raise ValueError("Grading parameters cannot be negative.")

    @abstractmethod
    def _apply_grading_strategy(self, params: dict) -> GradeResult:
        pass

    def _calculate_assessed_value(self, base_price_paise: int, multiplier: float) -> int:
        return int(base_price_paise * multiplier)
```

---

## 5. SOLID Principles Proof Matrix (Member 2)

1. **Single Responsibility Principle (SRP)**:
   - `LotService` is responsible solely for lot lifecycle state transitions (`available` $\to$ `locked`).
   - `GradingEngine` is responsible solely for the agro-physical quality rules and advice.
2. **Open/Closed Principle (OCP)**:
   - When introducing a new crop (e.g. Cotton or Maize), we simply create `CottonGradingStrategy` implementing `IGradingStrategy`. We never touch or re-test existing Onion or Soybean grading code.
3. **Liskov Substitution Principle (LSP)**:
   - Any subclass of `IGradingStrategy` can seamlessly be passed into `BaseLotAssessor` without breaking contract expectations.
4. **Interface Segregation Principle (ISP)**:
   - `IGradingStrategy` exposes only `evaluate()`, ensuring grading algorithms aren't burdened with persistence or HTTP logic.
5. **Dependency Inversion Principle (DIP)**:
   - `LotService` depends on `ILotRepository` (from Member 1's base architecture) and `IGradingStrategy`, injected dynamically.

---

## 6. Pytest Automated Test Suite

Save in `tests/test_member_2_lots_grading.py`:

```python
import pytest
from app.engines.strategies.grading_strategy import OnionGradingStrategy

def test_onion_grade_a():
    strategy = OnionGradingStrategy()
    result = strategy.evaluate({"moisture_pct": 11.0, "size_uniformity_pct": 90.0})
    assert result.grade == "A"
    assert result.assessed_multiplier == 1.0

def test_onion_grade_b_with_tips():
    strategy = OnionGradingStrategy()
    result = strategy.evaluate({"moisture_pct": 14.0, "size_uniformity_pct": 75.0})
    assert result.grade == "B"
    assert result.assessed_multiplier == 0.85
    assert len(result.tips) > 0

def test_onion_grade_c():
    strategy = OnionGradingStrategy()
    result = strategy.evaluate({"moisture_pct": 18.0, "size_uniformity_pct": 60.0})
    assert result.grade == "C"
    assert result.assessed_multiplier == 0.70
```

---

## 7. Faculty Viva Defense Guide (Member 2)

* **Faculty Q: "Why use the Strategy Pattern for grading instead of just writing multiple `if/elif` conditions?"**
  * *Answer:* *"Hardcoded `if/elif` branches violate the Open/Closed Principle. If we have 50 agricultural commodities with varying AGMARKNET moisture and size guidelines, an `if/elif` method turns into hundreds of lines of brittle code. With the Strategy pattern, each crop has its own isolated strategy class. We can add, test, and tune Soybean grading without risking Onion or Tomato grading logic."*

* **Faculty Q: "How does your Template Method pattern preserve domain integrity?"**
  * *Answer:* *"The `BaseLotAssessor` template method enforces an invariant sequence: inputs must be validated before grading, and the financial assessed value must scale deterministically ($A=100\%$, $B=85\%$, $C=70\%$) before advice is generated. Concrete subclasses can customize the grading algorithm, but cannot alter the overarching assessment lifecycle."*

