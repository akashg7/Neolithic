"""Agent-tool tests run without Postgres: the reference catalog is built in memory
and DB-backed services are monkeypatched per test."""

import time
from types import SimpleNamespace

import pytest
import pytest_asyncio

from app.utils import id_resolver


@pytest_asyncio.fixture(autouse=True)
async def setup_db():
    """Override the parent conftest's autouse DB setup: these tests need no DB."""
    yield


def build_catalog() -> id_resolver.Catalog:
    c = id_resolver.Catalog()
    for i, (name, mr) in enumerate([
        ("Onion", "कांदा"), ("Soyabean", "सोयाबीन"), ("Wheat", "गहू"),
        ("Tomato", "टोमॅटो"), ("Bengal Gram", "हरभरा"),
    ], start=1):
        c.add("commodity", id=i, name=name, name_mr=mr)
    for i, (name, mr) in enumerate([
        ("Nashik", "नाशिक"), ("Pune", "पुणे"), ("Ahmednagar", "अहिल्यानगर"),
        ("Chhatrapati Sambhajinagar", "छत्रपती संभाजीनगर"),
    ], start=1):
        c.add("district", id=i, name=name, name_mr=mr)
    for i, (name, mr, d, lat, lng) in enumerate([
        ("Lasalgaon APMC", "लासलगाव कृषी उत्पन्न बाजार समिती", 1, 20.1438, 74.2386),
        ("Nashik APMC", "नाशिक कृषी उत्पन्न बाजार समिती", 1, 19.9975, 73.7898),
        ("Pune APMC", "पुणे कृषी उत्पन्न बाजार समिती (गुलटेकडी)", 2, 18.4967, 73.8647),
        ("Pune(Moshi) APMC", "पुणे (मोशी) कृषी उत्पन्न बाजार समिती", 2, 18.6756, 73.8441),
        ("Ahilyanagar APMC", "अहिल्यानगर बाजार समिती", 3, 19.0952, 74.7496),
        ("Pimpalgaon APMC", "पिंपळगाव बाजार समिती", 1, 20.1700, 73.9900),
        ("Pimpalner APMC", "पिंपळनेर बाजार समिती", 1, 20.9500, 74.1500),
    ], start=1):
        c.add("market", id=i, name=name, name_mr=mr, district_id=d, lat=lat, lng=lng)
    return c


@pytest.fixture
def catalog():
    return build_catalog()


@pytest.fixture(autouse=True)
def process_catalog(monkeypatch):
    """Make `id_resolver.resolve()` use the in-memory catalog (no DB round-trip)."""
    c = build_catalog()
    monkeypatch.setattr(id_resolver._catalog, "_idx", c._idx)
    monkeypatch.setattr(id_resolver._catalog, "loaded", True)
    monkeypatch.setattr(id_resolver, "_loaded_at", time.monotonic())
    yield


@pytest.fixture
def farmer():
    return SimpleNamespace(id=1, role="FARMER", lat=20.0059, lng=74.05, district_id=1, locale="mr")


@pytest.fixture
def buyer():
    return SimpleNamespace(id=2, role="BUYER", lat=None, lng=None, district_id=None, locale="en")
