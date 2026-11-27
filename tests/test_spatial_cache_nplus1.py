"""Unit tests for PostGIS spatial SQL builders, resilient Redis HTTP cache, and N+1 batching."""
from __future__ import annotations

from types import SimpleNamespace
from typing import Optional

import httpx
import pytest
import pytest_asyncio
from fastapi import Depends, FastAPI
from fastapi_cache import Backend, FastAPICache
from sqlalchemy.dialects import postgresql

from app.models.lot import Lot
from app.models.mandi import MandiLocation
from app.models.transaction import Transaction
from app.repositories.fpo_repository import IFpoRepository
from app.repositories.lot_repository import ILotRepository
from app.repositories.transaction_repository import (
    IEscrowEventRepository,
    SQLAlchemyTransactionRepository,
)
from app.services.lot_pool_service import LotPoolService
from app.services.transaction_service import TransactionService
from app.utils.cache import safe_cache
from app.utils.spatial import (
    distance_km_expr,
    is_postgres,
    make_wkt_point,
    within_radius_filter,
)


@pytest_asyncio.fixture(autouse=True)
async def setup_db():
    """Override conftest Postgres setup; these tests require no external DB."""
    yield


class _InMemoryCacheBackend(Backend):
    def __init__(self) -> None:
        self.store: dict[str, bytes] = {}
        self.ttls: dict[str, int] = {}

    async def get_with_ttl(self, key: str) -> tuple[int, Optional[bytes]]:
        if key not in self.store:
            return 0, None
        return self.ttls.get(key, 60), self.store[key]

    async def get(self, key: str) -> Optional[bytes]:
        return self.store.get(key)

    async def set(self, key: str, value: bytes, expire: Optional[int] = None) -> None:
        self.store[key] = value
        self.ttls[key] = expire or 60

    async def clear(self, namespace: Optional[str] = None, key: Optional[str] = None) -> int:
        if key:
            return int(self.store.pop(key, None) is not None)
        if namespace:
            keys = [k for k in self.store if k.startswith(namespace)]
            for k in keys:
                self.store.pop(k, None)
            return len(keys)
        n = len(self.store)
        self.store.clear()
        return n


def test_spatial_helpers_compile_postgis_sql():
    assert is_postgres(None) is False
    assert is_postgres(SimpleNamespace()) is False
    assert make_wkt_point(None, 74.2) is None
    wkt = make_wkt_point(20.1438, 74.2386)
    assert wkt is not None and wkt.srid == 4326 and "74.2386 20.1438" in wkt.desc

    pg_dialect = postgresql.dialect()
    filt_sql = str(within_radius_filter(MandiLocation.geom, 20.1438, 74.2386, 150.0).compile(dialect=pg_dialect))
    dist_sql = str(distance_km_expr(MandiLocation.geom, 20.1438, 74.2386).compile(dialect=pg_dialect))
    assert "&&" in filt_sql
    assert "ST_MakeEnvelope" in filt_sql
    assert "ST_DWithin" in filt_sql
    assert "geography" in filt_sql.lower()
    assert "ST_Distance" in dist_sql


@pytest.mark.asyncio
async def test_safe_cache_bypasses_when_uninitialized_and_caches_when_ready():
    FastAPICache.reset()
    calls = {"n": 0}
    current_user = {"user": SimpleNamespace(id=1)}

    app = FastAPI()

    @app.get("/items")
    @safe_cache(expire=120, namespace="test")
    async def list_items(q: str = "a"):
        calls["n"] += 1
        return {"q": q, "call": calls["n"]}

    @app.get("/scoped")
    @safe_cache(expire=120, namespace="scoped", user_scoped=True)
    async def scoped_items(user=Depends(lambda: current_user["user"])):
        calls["n"] += 1
        return {"uid": user.id, "call": calls["n"]}

    async with httpx.AsyncClient(transport=httpx.ASGITransport(app=app), base_url="http://test") as client:
        # Uninitialized FastAPICache -> transparent pass-through
        r1 = await client.get("/items?q=onion")
        r2 = await client.get("/items?q=onion")
        assert r1.status_code == 200 and r2.status_code == 200
        assert r1.json()["call"] == 1 and r2.json()["call"] == 2

        backend = _InMemoryCacheBackend()
        FastAPICache.init(backend, prefix="test-cache")
        try:
            m1 = await client.get("/items?q=onion")
            assert m1.headers["X-FastAPI-Cache"] == "MISS"
            assert m1.json()["call"] == 3

            h1 = await client.get("/items?q=onion")
            assert h1.headers["X-FastAPI-Cache"] == "HIT"
            assert h1.json()["call"] == 3

            # Cache-Control: no-cache bypasses cached payload
            b1 = await client.get("/items?q=onion", headers={"Cache-Control": "no-cache"})
            assert b1.headers["X-FastAPI-Cache"] == "MISS"
            assert b1.json()["call"] == 4

            # User-scoped routes isolate keys by user.id
            u1_miss = await client.get("/scoped")
            u1_hit = await client.get("/scoped")
            assert u1_miss.json()["uid"] == 1 and u1_hit.headers["X-FastAPI-Cache"] == "HIT"

            current_user["user"] = SimpleNamespace(id=2)
            u2_miss = await client.get("/scoped")
            assert u2_miss.headers["X-FastAPI-Cache"] == "MISS"
            assert u2_miss.json()["uid"] == 2
        finally:
            FastAPICache.reset()


@pytest.mark.asyncio
async def test_lot_pool_uses_batched_fpo_lookup_instead_of_n_plus_1():
    class CountingLotRepo(ILotRepository):
        def __init__(self, lots):
            self.lots = {l.id: l for l in lots}
            self.next_id = 100

        async def get_by_id(self, id): return self.lots.get(id)
        async def list(self, skip=0, limit=100): return list(self.lots.values())
        async def create(self, entity):
            entity.id = self.next_id
            self.next_id += 1
            self.lots[entity.id] = entity
            return entity
        async def update(self, entity): return entity
        async def delete(self, id): return False
        async def commit(self): pass
        async def list_for_farmer(self, farmer_id, status=None): return []
        async def get_many(self, lot_ids, lock=False): return [self.lots[i] for i in lot_ids if i in self.lots]
        async def add_batch_member(self, member): return member

    class CountingFpoRepo(IFpoRepository):
        def __init__(self):
            self.single_calls = 0
            self.batch_calls = 0

        async def get_by_id(self, id): return None
        async def list(self, skip=0, limit=100): return []
        async def create(self, entity): return entity
        async def update(self, entity): return entity
        async def delete(self, id): return False
        async def commit(self): pass
        async def list_farmers(self, fpo_id): return []

        async def get_fpo_id_for_user(self, user_id: int) -> Optional[int]:
            self.single_calls += 1
            return 10

        async def get_fpo_ids_for_users(self, user_ids):
            self.batch_calls += 1
            return {uid: 10 for uid in user_ids}

    lots = [
        Lot(id=i, farmer_id=i, commodity_id=1, quantity_qtl=10, expected_price_paise=200000, grade="A", status="active")
        for i in range(1, 6)
    ]
    fpo_repo = CountingFpoRepo()
    svc = LotPoolService(CountingLotRepo(lots), fpo_repo)
    admin = SimpleNamespace(id=99, role="FPO_ADMIN")
    batch = await svc.pool(admin, [1, 2, 3, 4, 5])
    assert batch.quantity_qtl == 50
    assert fpo_repo.single_calls == 1  # only admin lookup
    assert fpo_repo.batch_calls == 1   # 1 batched query for all 5 farmer lots


@pytest.mark.asyncio
async def test_transaction_service_skips_duplicate_event_query_for_sqlalchemy_repo():
    class FakeSQLATxnRepo(SQLAlchemyTransactionRepository):
        def __init__(self):
            pass

        async def get_with_events(self, transaction_id: int):
            t = Transaction(id=transaction_id, offer_id=1, buyer_id=2, farmer_id=1, amount_paise=10000, status="CREATED")
            t.events = []
            return t

    class SpyEventRepo(IEscrowEventRepository):
        def __init__(self):
            self.calls = 0

        async def get_by_id(self, id): return None
        async def list(self, skip=0, limit=100): return []
        async def create(self, entity): return entity
        async def update(self, entity): return entity
        async def delete(self, id): return False
        async def commit(self): pass

        async def list_for_transaction(self, transaction_id: int):
            self.calls += 1
            return []

        async def log_event(self, transaction_id, from_state, to_state, actor_id=None, note=None):
            return SimpleNamespace(id=1)

    ev_repo = SpyEventRepo()
    svc = TransactionService(FakeSQLATxnRepo(), ev_repo)
    txn = await svc.get_transaction(SimpleNamespace(id=1), 42)
    assert txn.id == 42
    assert ev_repo.calls == 0
