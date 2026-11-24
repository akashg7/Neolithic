"""Offline tests for Person A (Agent schemas, LLM client, tools, guards, loop, router)."""
from __future__ import annotations

import time
from types import SimpleNamespace

import pytest
import pytest_asyncio

from app.utils import id_resolver


@pytest_asyncio.fixture(autouse=True)
async def setup_db():
    """Override the repo-wide Postgres autouse fixture: all tests here run offline."""
    yield


def build_catalog() -> id_resolver.Catalog:
    c = id_resolver.Catalog()
    for i, (name, mr) in enumerate(
        [
            ("Onion", "कांदा"),
            ("Soyabean", "सोयाबीन"),
            ("Wheat", "गहू"),
            ("Tomato", "टोमॅटो"),
            ("Bengal Gram", "हरभरा"),
        ],
        start=1,
    ):
        c.add("commodity", id=i, name=name, name_mr=mr)
    for i, (name, mr) in enumerate(
        [
            ("Nashik", "नाशिक"),
            ("Pune", "पुणे"),
            ("Ahmednagar", "अहिल्यानगर"),
            ("Chhatrapati Sambhajinagar", "छत्रपती संभाजीनगर"),
        ],
        start=1,
    ):
        c.add("district", id=i, name=name, name_mr=mr)
    for i, (name, mr, d, lat, lng) in enumerate(
        [
            ("Lasalgaon APMC", "लासलगाव कृषी उत्पन्न बाजार समिती", 1, 20.1438, 74.2386),
            ("Nashik APMC", "नाशिक कृषी उत्पन्न बाजार समिती", 1, 19.9975, 73.7898),
            ("Pune APMC", "पुणे कृषी उत्पन्न बाजार समिती (गुलटेकडी)", 2, 18.4967, 73.8647),
            ("Pune(Moshi) APMC", "पुणे (मोशी) कृषी उत्पन्न बाजार समिती", 2, 18.6756, 73.8441),
            ("Ahilyanagar APMC", "अहिल्यानगर बाजार समिती", 3, 19.0952, 74.7496),
            ("Pimpalgaon APMC", "पिंपळगाव बाजार समिती", 1, 20.1700, 73.9900),
            ("Pimpalner APMC", "पिंपळनेर बाजार समिती", 1, 20.9500, 74.1500),
        ],
        start=1,
    ):
        c.add("market", id=i, name=name, name_mr=mr, district_id=d, lat=lat, lng=lng)
    return c


@pytest.fixture(autouse=True)
def process_catalog(monkeypatch):
    c = build_catalog()
    monkeypatch.setattr(id_resolver._catalog, "_idx", c._idx)
    monkeypatch.setattr(id_resolver._catalog, "loaded", True)
    monkeypatch.setattr(id_resolver, "_loaded_at", time.monotonic())
    yield


@pytest.fixture
def farmer():
    return SimpleNamespace(
        id=1,
        name="Ramesh Patil",
        phone="9822011111",
        role="FARMER",
        lat=20.0059,
        lng=74.05,
        district_id=1,
        village="Niphad",
        locale="mr",
    )


@pytest.fixture
def buyer():
    return SimpleNamespace(
        id=2,
        name="Mehta Traders",
        phone="9822022222",
        role="BUYER",
        lat=None,
        lng=None,
        district_id=None,
        village=None,
        locale="en",
    )


class FakeAsyncRedis:
    """Minimal async in-memory Redis mock supporting get/set/delete."""

    def __init__(self) -> None:
        self.store: dict[str, str] = {}
        self.ttls: dict[str, int | None] = {}

    async def get(self, key: str):
        return self.store.get(key)

    async def set(self, key: str, value: str, ex: int | None = None):
        self.store[key] = value
        self.ttls[key] = ex
        return True

    async def delete(self, key: str) -> int:
        existed = 1 if key in self.store else 0
        self.store.pop(key, None)
        self.ttls.pop(key, None)
        return existed


@pytest.fixture
def fake_redis():
    return FakeAsyncRedis()
