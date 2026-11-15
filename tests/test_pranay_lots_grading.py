"""Pranay — grading strategies, template-method assessor, lot lifecycle,
lot grading service, FPO lot pooling, and the HTTP endpoints.

No Postgres needed. Services depend on repository interfaces, so the tests
inject small in-memory repositories.
"""
from itertools import count
from types import SimpleNamespace
from typing import Optional, Sequence

import pytest
import pytest_asyncio
from fastapi import FastAPI, HTTPException
from httpx import ASGITransport, AsyncClient

from app.dependencies.auth import get_current_user
from app.dependencies.lots import (
    get_commodity_repository,
    get_lot_repository,
)
from app.dependencies.repositories import get_fpo_repository
from app.domain import lot_lifecycle
from app.engines.lot_assessor import GradingInputError, StrategyLotAssessor
from app.engines.strategies.grading_strategy import (
    GradeResult,
    GradingStrategyRegistry,
    IGradingStrategy,
    OilseedGrainGradingStrategy,
    OnionGradingStrategy,
    PerishableVegetableGradingStrategy,
    build_default_registry,
)
from app.models.lot import Lot
from app.repositories.fpo_repository import IFpoRepository
from app.repositories.lot_repository import ICommodityRepository, ILotRepository
from app.routers import fpo as fpo_router
from app.routers import lots as lots_router
from app.schemas.lot import GradeRequest, LotOut
from app.services.lot_grading_service import LotGradingService
from app.services.lot_pool_service import LotPoolService


@pytest_asyncio.fixture(autouse=True)
async def setup_db():
    """Override conftest's Postgres create/drop: this module uses in-memory repos."""
    yield


# ── LLD §6 tests, verbatim ───────────────────────────────────────────────────

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


# ── Other strategies ────────────────────────────────────────────────────────

@pytest.mark.parametrize("params, grade", [
    ({"moisture_pct": 9, "foreign_matter_pct": 0.5}, "A"),
    ({"moisture_pct": 11.5, "foreign_matter_pct": 1.5}, "B"),
    ({"moisture_pct": 14, "foreign_matter_pct": 0.5}, "C"),
    ({"moisture_pct": 9, "foreign_matter_pct": 3}, "C"),
    ({"moisture_pct": 9, "foreign_matter_pct": 0.5, "damage_pct": 4}, "B"),
])
def test_oilseed_grain_grades(params, grade):
    assert OilseedGrainGradingStrategy().evaluate(params).grade == grade


@pytest.mark.parametrize("params, grade", [
    ({"damage_pct": 1, "size_uniformity_pct": 90}, "A"),
    ({"damage_pct": 5, "size_uniformity_pct": 90}, "B"),
    ({"damage_pct": 1, "size_uniformity_pct": 90, "discoloration_pct": 10}, "B"),
    ({"damage_pct": 12, "size_uniformity_pct": 90}, "C"),
])
def test_perishable_grades(params, grade):
    assert PerishableVegetableGradingStrategy().evaluate(params).grade == grade


def test_every_non_a_grade_gives_advice():
    for strategy, params in [
        (OnionGradingStrategy(), {"moisture_pct": 13, "size_uniformity_pct": 90}),
        (OilseedGrainGradingStrategy(), {"moisture_pct": 15, "foreign_matter_pct": 4}),
        (PerishableVegetableGradingStrategy(), {"damage_pct": 20, "size_uniformity_pct": 50}),
    ]:
        result = strategy.evaluate(params)
        assert result.grade in ("B", "C")
        assert result.tips, f"{strategy.name} gave no advice"


def test_registry_picks_strategy_by_commodity_name():
    registry = build_default_registry()
    assert isinstance(registry.for_commodity("Onion"), OnionGradingStrategy)
    assert isinstance(registry.for_commodity("soyabean"), OilseedGrainGradingStrategy)
    assert isinstance(registry.for_commodity("  Tomato "), PerishableVegetableGradingStrategy)
    with pytest.raises(ValueError):
        registry.for_commodity("Dragon Fruit")


def test_new_crop_is_added_without_touching_existing_code():
    """OCP: a new crop is a new class + one register() call."""
    class CottonGradingStrategy(IGradingStrategy):
        name = "cotton"
        required_params = ("trash_pct",)

        def evaluate(self, params):
            return GradeResult("A" if params["trash_pct"] < 3 else "C",
                               1.0 if params["trash_pct"] < 3 else 0.70, [])

    registry = build_default_registry()
    registry.register("Cotton", CottonGradingStrategy())
    assert registry.for_commodity("Cotton").name == "cotton"
    assert isinstance(registry.for_commodity("Onion"), OnionGradingStrategy)


# ── Template method: BaseLotAssessor ────────────────────────────────────────

def _lot(**kw):
    base = dict(id=7, farmer_id=1, commodity_id=1, quantity_qtl=25,
                expected_price_paise=220_000, grade=None, status="active")
    base.update(kw)
    return SimpleNamespace(**base)


def test_assessor_runs_all_steps_and_uses_integer_money():
    result = StrategyLotAssessor(OnionGradingStrategy()).assess_lot(
        _lot(), {"moisture_pct": 14, "size_uniformity_pct": 75})
    assert result.grade == "B"
    assert result.strategy == "onion"
    assert result.assessed_price_paise_per_qtl == 187_000          # 220000 * 0.85
    assert result.assessed_value_paise == 187_000 * 25
    assert isinstance(result.assessed_price_paise_per_qtl, int)
    assert result.advice


def test_assessor_rounds_down_odd_paise():
    result = StrategyLotAssessor(OnionGradingStrategy()).assess_lot(
        _lot(expected_price_paise=100_001), {"moisture_pct": 14, "size_uniformity_pct": 75})
    assert result.assessed_price_paise_per_qtl == 85_000  # 100001 * 8500 // 10000


def test_assessor_without_price_still_grades():
    result = StrategyLotAssessor(OnionGradingStrategy()).assess_lot(
        _lot(expected_price_paise=None), {"moisture_pct": 11, "size_uniformity_pct": 90})
    assert result.grade == "A"
    assert result.assessed_price_paise_per_qtl is None
    assert result.assessed_value_paise is None


@pytest.mark.parametrize("params, message", [
    ({"moisture_pct": -1, "size_uniformity_pct": 90}, "negative"),
    ({"moisture_pct": 10, "size_uniformity_pct": 120}, "above 100"),
    ({"moisture_pct": 10}, "Missing required"),
    ({"moisture_pct": "wet", "size_uniformity_pct": 90}, "must be a number"),
])
def test_assessor_validates_before_grading(params, message):
    with pytest.raises(GradingInputError, match=message):
        StrategyLotAssessor(OnionGradingStrategy()).assess_lot(_lot(), params)


# ── Lot lifecycle ────────────────────────────────────────────────────────────

def test_lifecycle_allows_only_legal_moves():
    lot = _lot(status="active")
    lot_lifecycle.transition(lot, lot_lifecycle.LOCKED)
    lot_lifecycle.transition(lot, lot_lifecycle.SOLD)
    assert lot.status == "sold"
    with pytest.raises(lot_lifecycle.InvalidLotTransition):
        lot_lifecycle.transition(lot, lot_lifecycle.ACTIVE)


def test_locked_lot_can_be_released_back_to_active():
    lot = _lot(status="locked")
    lot_lifecycle.transition(lot, lot_lifecycle.ACTIVE)
    assert lot.status == "active"


def test_lotout_maps_new_statuses_into_api_enum():
    for db_status, api_status in [("active", "LISTED"), ("locked", "OFFERED"),
                                  ("pooled", "POOLED"), ("sold", "SOLD")]:
        out = LotOut.model_validate(_lot(status=db_status, market_id=None, warehouse_id=None,
                                         image_url=None, created_at=None))
        assert out.status == api_status


# ── In-memory repositories ──────────────────────────────────────────────────

class InMemoryLotRepo(ILotRepository):
    def __init__(self, lots: Sequence = ()):
        self.rows = {lot.id: lot for lot in lots}
        self._ids = count(1000)
        self.members = []

    async def get_by_id(self, id):
        return self.rows.get(id)

    async def list(self, skip=0, limit=100):
        return list(self.rows.values())[skip:skip + limit]

    async def create(self, entity):
        if getattr(entity, "id", None) is None:
            entity.id = next(self._ids)
        self.rows[entity.id] = entity
        return entity

    async def update(self, entity):
        self.rows[entity.id] = entity
        return entity

    async def delete(self, id):
        return self.rows.pop(id, None) is not None

    async def commit(self):
        pass

    async def list_for_farmer(self, farmer_id, status=None):
        return [l for l in self.rows.values()
                if l.farmer_id == farmer_id and (status is None or l.status == status)]

    async def get_many(self, lot_ids, lock=False):
        self.last_lock = lock
        return [self.rows[i] for i in lot_ids if i in self.rows]

    async def add_batch_member(self, member):
        self.members.append(member)
        return member


class InMemoryCommodityRepo(ICommodityRepository):
    NAMES = {1: "Onion", 2: "Soyabean", 4: "Tomato", 99: "Dragon Fruit"}

    async def get_by_id(self, id): return None
    async def list(self, skip=0, limit=100): return []
    async def create(self, entity): return entity
    async def update(self, entity): return entity
    async def delete(self, id): return False
    async def commit(self): pass

    async def get_name(self, commodity_id):
        return self.NAMES.get(commodity_id)


class InMemoryFpoRepo(IFpoRepository):
    def __init__(self, fpo_of_user: dict):
        self.fpo_of_user = fpo_of_user

    async def get_by_id(self, id): return None
    async def list(self, skip=0, limit=100): return []
    async def create(self, entity): return entity
    async def update(self, entity): return entity
    async def delete(self, id): return False
    async def commit(self): pass

    async def get_fpo_id_for_user(self, user_id) -> Optional[int]:
        return self.fpo_of_user.get(user_id)

    async def list_farmers(self, fpo_id):
        return []


def _db_lot(id, farmer_id=1, commodity_id=1, qtl=10, price=200_000, grade=None, status="active"):
    return Lot(id=id, farmer_id=farmer_id, commodity_id=commodity_id, quantity_qtl=qtl,
               expected_price_paise=price, grade=grade, status=status, lat=20.0, lng=74.0)


FARMER = SimpleNamespace(id=1, role="FARMER")
OTHER_FARMER = SimpleNamespace(id=2, role="FARMER")
ADMIN = SimpleNamespace(id=3, role="FPO_ADMIN")


# ── LotGradingService ───────────────────────────────────────────────────────

def _grading_service(*lots):
    repo = InMemoryLotRepo(lots)
    return repo, LotGradingService(repo, InMemoryCommodityRepo(), build_default_registry())


@pytest.mark.asyncio
async def test_grading_service_saves_grade_on_lot():
    repo, service = _grading_service(_db_lot(1, qtl=25, price=220_000))
    out = await service.grade_lot(FARMER, 1, GradeRequest(moisture_pct=11, size_uniformity_pct=90))
    assert out.grade == "A"
    assert out.commodity == "Onion"
    assert out.assessed_value_paise == 220_000 * 25
    assert repo.rows[1].grade == "A"


@pytest.mark.asyncio
async def test_grading_service_uses_the_crop_strategy():
    _, service = _grading_service(_db_lot(1, commodity_id=2))
    out = await service.grade_lot(FARMER, 1, GradeRequest(moisture_pct=11.5, foreign_matter_pct=1.5))
    assert out.strategy == "oilseed_grain"
    assert out.grade == "B"


@pytest.mark.asyncio
async def test_grading_someone_elses_lot_is_404():
    _, service = _grading_service(_db_lot(1, farmer_id=1))
    with pytest.raises(HTTPException) as exc:
        await service.grade_lot(OTHER_FARMER, 1, GradeRequest(moisture_pct=11, size_uniformity_pct=90))
    assert exc.value.status_code == 404


@pytest.mark.asyncio
@pytest.mark.parametrize("lot, payload, code", [
    (_db_lot(1, status="sold"), GradeRequest(moisture_pct=11, size_uniformity_pct=90), 409),
    (_db_lot(1, commodity_id=99), GradeRequest(moisture_pct=11, size_uniformity_pct=90), 422),
    (_db_lot(1), GradeRequest(moisture_pct=11), 422),  # onion needs size uniformity too
])
async def test_grading_service_errors(lot, payload, code):
    _, service = _grading_service(lot)
    with pytest.raises(HTTPException) as exc:
        await service.grade_lot(FARMER, 1, payload)
    assert exc.value.status_code == code


# ── LotPoolService ──────────────────────────────────────────────────────────

def _pool_service(*lots, fpo_of_user=None):
    repo = InMemoryLotRepo(lots)
    fpos = InMemoryFpoRepo(fpo_of_user or {1: 10, 2: 10, 3: 10, 4: 20})
    return repo, LotPoolService(repo, fpos)


@pytest.mark.asyncio
async def test_pool_merges_lots_into_one_batch():
    repo, service = _pool_service(
        _db_lot(1, farmer_id=1, qtl=10, price=200_000, grade="A"),
        _db_lot(2, farmer_id=2, qtl=30, price=240_000, grade="B"),
    )
    batch = await service.pool(ADMIN, [1, 2])

    assert batch.quantity_qtl == 40
    assert batch.grade == "B"                                      # lowest member grade
    assert batch.expected_price_paise == (200_000 * 10 + 240_000 * 30) // 40
    assert batch.status == "active"
    assert [m.quantity_contributed_qtl for m in batch.member_lots] == [10, 30]
    assert repo.rows[1].status == "pooled" and repo.rows[2].status == "pooled"
    assert [m.quantity_contributed_kg for m in repo.members] == [1000, 3000]
    stored = repo.rows[batch.id]
    assert stored.fpo_id == 10 and stored.farmer_id == ADMIN.id
    assert repo.last_lock is True        # source lots were row-locked


@pytest.mark.asyncio
async def test_pooling_the_same_lots_twice_is_rejected():
    _, service = _pool_service(_db_lot(1), _db_lot(2, farmer_id=2))
    await service.pool(ADMIN, [1, 2])
    with pytest.raises(HTTPException) as exc:
        await service.pool(ADMIN, [1, 2])
    assert exc.value.status_code == 409


@pytest.mark.asyncio
async def test_pool_with_an_ungraded_lot_gives_ungraded_batch():
    _, service = _pool_service(_db_lot(1, grade="A"), _db_lot(2, farmer_id=2, grade=None))
    assert (await service.pool(ADMIN, [1, 2])).grade is None


@pytest.mark.asyncio
@pytest.mark.parametrize("lots, ids, kwargs, code", [
    ([_db_lot(1), _db_lot(2, farmer_id=4)], [1, 2], {}, 404),            # farmer 4 is in another FPO
    ([_db_lot(1)], [1, 2], {}, 404),                                     # lot 2 doesn't exist
    ([_db_lot(1), _db_lot(2, commodity_id=2)], [1, 2], {}, 400),         # mixed crops
    ([_db_lot(1), _db_lot(2, status="sold")], [1, 2], {}, 409),          # not active
    ([_db_lot(1), _db_lot(2)], [1, 1], {}, 400),                         # duplicates
    ([_db_lot(1)], [1], {}, 400),                                        # only one lot
    ([_db_lot(1), _db_lot(2)], [1, 2], {"fpo_id": 20}, 404),             # someone else's FPO
])
async def test_pool_rejects_bad_requests(lots, ids, kwargs, code):
    _, service = _pool_service(*lots)
    with pytest.raises(HTTPException) as exc:
        await service.pool(ADMIN, ids, **kwargs)
    assert exc.value.status_code == code


@pytest.mark.asyncio
async def test_pool_by_admin_without_fpo_is_404():
    _, service = _pool_service(_db_lot(1), _db_lot(2), fpo_of_user={1: 10, 2: 10})
    with pytest.raises(HTTPException) as exc:
        await service.pool(ADMIN, [1, 2])
    assert exc.value.status_code == 404


# ── HTTP: POST /api/v1/lots/{id}/grade and POST /api/v1/fpo/lots/pool ───────

@pytest_asyncio.fixture
async def http():
    lot_repo = InMemoryLotRepo([
        _db_lot(1, farmer_id=1, qtl=10, grade="A"),
        _db_lot(2, farmer_id=2, qtl=15, grade="B"),
        _db_lot(3, farmer_id=1, qtl=20),
    ])
    state = {"user": FARMER}
    app = FastAPI()
    app.include_router(lots_router.router, prefix="/api/v1/lots")
    app.include_router(fpo_router.router, prefix="/api/v1/pools")
    app.include_router(fpo_router.farmers_router, prefix="/api/v1/fpo")
    app.dependency_overrides[get_current_user] = lambda: state["user"]
    app.dependency_overrides[get_lot_repository] = lambda: lot_repo
    app.dependency_overrides[get_commodity_repository] = lambda: InMemoryCommodityRepo()
    app.dependency_overrides[get_fpo_repository] = lambda: InMemoryFpoRepo({1: 10, 2: 10, 3: 10})
    async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as client:
        yield client, state, lot_repo


@pytest.mark.asyncio
async def test_http_grade_lot(http):
    client, state, repo = http
    res = await client.post("/api/v1/lots/3/grade",
                            json={"moisture_pct": 12.5, "foreign_matter_pct": 1.2, "size_uniformity_pct": 88})
    assert res.status_code == 200, res.text
    body = res.json()
    assert body["grade"] == "B"
    assert body["assessed_price_paise_per_qtl"] == 170_000
    assert body["advice"]
    assert repo.rows[3].grade == "B"


@pytest.mark.asyncio
async def test_http_grade_rejects_out_of_range_and_foreign_lots(http):
    client, state, _ = http
    bad = await client.post("/api/v1/lots/3/grade", json={"moisture_pct": 150, "size_uniformity_pct": 80})
    assert bad.status_code == 422
    other = await client.post("/api/v1/lots/2/grade", json={"moisture_pct": 10, "size_uniformity_pct": 90})
    assert other.status_code == 404


@pytest.mark.asyncio
async def test_http_pool_lots_as_fpo_admin(http):
    client, state, repo = http
    state["user"] = ADMIN
    res = await client.post("/api/v1/fpo/lots/pool", json={"lot_ids": [1, 2], "fpo_id": 10})
    assert res.status_code == 201, res.text
    body = res.json()
    assert body["quantity_qtl"] == 25
    assert body["grade"] == "B"
    assert len(body["member_lots"]) == 2


@pytest.mark.asyncio
async def test_http_old_aggregate_endpoint_works_again(http):
    client, state, _ = http
    state["user"] = ADMIN
    res = await client.post("/api/v1/pools/aggregate", json={"lot_ids": [1, 2]})
    assert res.status_code == 201, res.text


@pytest.mark.asyncio
async def test_http_farmer_cannot_pool(http):
    client, state, _ = http
    res = await client.post("/api/v1/fpo/lots/pool", json={"lot_ids": [1, 2]})
    assert res.status_code == 404
