"""Member 5 patterns, API contracts and advisory invariants; no DB or live API."""
import asyncio
import base64
from unittest.mock import AsyncMock

import httpx
import pytest
import pytest_asyncio
from fastapi import FastAPI

from app.adapters.cached_voice_decorator import CachedVoiceDecorator
from app.adapters.voice_adapter import MockVoiceAdapter, SarvamVoiceAdapter
from app.adapters.voice_provider import IVoiceProvider, VoiceEngineError
from app.dependencies.voice import get_voice_provider
from app.engines import price_engine as pe
from app.engines import window_engine as we
from app.domain.costs import CostBreakdown
from app.domain.pledge import quote
from app.domain.window import WindowResult
from app.routers import ai, voice


@pytest_asyncio.fixture(autouse=True)
async def setup_db():
    """Override the shared Postgres fixture: these tests inject their dependencies."""
    yield


class CountingProvider(MockVoiceAdapter):
    def __init__(self):
        self.calls = 0

    async def text_to_speech(self, text, *, language_code="mr-IN"):
        self.calls += 1
        return await super().text_to_speech(text, language_code=language_code)


@pytest.mark.asyncio
async def test_disk_cache_survives_decorator_recreation(tmp_path):
    provider = CountingProvider()
    cached = CachedVoiceDecorator(provider, tmp_path)
    first = await cached.text_to_speech("भाव", language_code="mr-IN")
    again = await CachedVoiceDecorator(provider, tmp_path).text_to_speech("भाव", language_code="mr-IN")
    assert first == again
    assert provider.calls == 1
    assert base64.b64decode(first["audio_base64"])[8:12] == b"WAVE"
    assert len(list(tmp_path.glob("*.json"))) == 1


@pytest.mark.asyncio
async def test_cache_separates_locale_text_and_model(tmp_path):
    provider = CountingProvider()
    cached = CachedVoiceDecorator(provider, tmp_path)
    await cached.text_to_speech("hello", language_code="mr-IN")
    await cached.text_to_speech("hello", language_code="en-IN")
    await cached.text_to_speech("different", language_code="en-IN")
    provider.cache_identity = "mock:changed-voice"
    await cached.text_to_speech("hello", language_code="mr-IN")
    assert provider.calls == 4


@pytest.mark.asyncio
async def test_corrupt_cache_is_regenerated(tmp_path):
    provider = CountingProvider()
    cached = CachedVoiceDecorator(provider, tmp_path)
    await cached.text_to_speech("hello")
    next(tmp_path.glob("*.json")).write_text("broken JSON")
    await cached.text_to_speech("hello")
    assert provider.calls == 2


@pytest.mark.asyncio
async def test_provider_error_is_not_cached(tmp_path):
    provider = MockVoiceAdapter()
    provider.text_to_speech = AsyncMock(side_effect=VoiceEngineError("unavailable"))
    cached = CachedVoiceDecorator(provider, tmp_path)
    for _ in range(2):
        with pytest.raises(VoiceEngineError):
            await cached.text_to_speech("hello")
    assert provider.text_to_speech.await_count == 2
    assert not list(tmp_path.glob("*.json"))


@pytest.mark.asyncio
async def test_invalid_audio_is_not_cached(tmp_path):
    provider = MockVoiceAdapter()
    provider.text_to_speech = AsyncMock(return_value={"audio_base64": "bad", "audio_format": "wav"})
    await CachedVoiceDecorator(provider, tmp_path).text_to_speech("hello")
    assert not list(tmp_path.glob("*.json"))


@pytest.mark.asyncio
async def test_unwritable_cache_does_not_break_speech(tmp_path):
    blocked = tmp_path / "file"
    blocked.write_text("not a directory")
    result = await CachedVoiceDecorator(MockVoiceAdapter(), blocked).text_to_speech("hello")
    assert result["audio_format"] == "wav"


@pytest.mark.asyncio
async def test_transcription_is_forwarded_without_caching(tmp_path):
    provider = MockVoiceAdapter()
    provider.speech_to_text = AsyncMock(return_value={"transcript": "hello"})
    cached = CachedVoiceDecorator(provider, tmp_path)
    assert await cached.speech_to_text(b"audio", filename="clip.wav", language_code="en-IN") == {"transcript": "hello"}
    provider.speech_to_text.assert_awaited_once_with(
        b"audio", filename="clip.wav", language_code="en-IN", mode="transcribe",
    )
    assert not list(tmp_path.glob("*.json"))


@pytest.mark.asyncio
async def test_concurrent_cache_writes_remain_readable(tmp_path):
    provider = CountingProvider()
    cached = CachedVoiceDecorator(provider, tmp_path)
    results = await asyncio.gather(*(cached.text_to_speech("hello") for _ in range(8)))
    assert all(result == results[0] for result in results)
    calls = provider.calls
    assert await cached.text_to_speech("hello") == results[0]
    assert provider.calls == calls
    assert len(list(tmp_path.iterdir())) == 1


@pytest.mark.parametrize("locale,language", [("mr", "mr-IN"), ("hi", "hi-IN"), ("en", "en-IN")])
@pytest.mark.asyncio
async def test_voice_routes_use_injected_provider(locale, language, tmp_path):
    provider = CountingProvider()
    app = FastAPI()
    app.include_router(voice.router, prefix="/api/v1/voice")
    app.dependency_overrides[get_voice_provider] = lambda: CachedVoiceDecorator(provider, tmp_path)
    async with httpx.AsyncClient(transport=httpx.ASGITransport(app=app), base_url="http://test") as client:
        for _ in range(2):
            res = await client.post("/api/v1/voice/narrate", json={"text": "hello", "locale": locale})
            assert res.status_code == 200
            assert res.json()["language_code"] == language
        res = await client.post("/api/v1/voice/transcribe", files={"audio": ("clip.wav", b"audio", "audio/wav")}, data={"locale": locale})
        assert res.status_code == 200
        assert res.json()["language_code"] == language
    assert provider.calls == 1


@pytest.mark.parametrize("configured,status", [(False, 503), (True, 502)])
@pytest.mark.asyncio
async def test_voice_route_failures(configured, status):
    provider = MockVoiceAdapter()
    provider.configured = configured
    provider.text_to_speech = AsyncMock(side_effect=VoiceEngineError("offline"))
    provider.speech_to_text = AsyncMock(side_effect=VoiceEngineError("offline"))
    app = FastAPI()
    app.include_router(voice.router)
    app.dependency_overrides[get_voice_provider] = lambda: provider
    async with httpx.AsyncClient(transport=httpx.ASGITransport(app=app), base_url="http://test") as client:
        assert (await client.post("/narrate", json={"text": "hello"})).status_code == status
        assert (await client.post("/transcribe", files={"file": ("a.wav", b"audio")})).status_code == status


def test_cache_setting_selects_decorator(monkeypatch):
    from app.config import settings
    from app.engines.voice_engine import voice_engine
    monkeypatch.setattr(settings, "VOICE_CACHE_ENABLED", False)
    assert get_voice_provider() is voice_engine
    monkeypatch.setattr(settings, "VOICE_CACHE_ENABLED", True)
    assert isinstance(get_voice_provider(), CachedVoiceDecorator)
    assert isinstance(SarvamVoiceAdapter(), IVoiceProvider)


def test_singleton_construction_does_not_reset_loaded_models(monkeypatch):
    sentinel = object()
    monkeypatch.setattr(pe.price_engine, "_loaded", True)
    monkeypatch.setattr(pe.price_engine, "_sota_predictor", sentinel)
    assert pe.PriceEngine() is pe.price_engine
    assert pe.PriceEngine()._sota_predictor is sentinel


def test_models_load_only_once(monkeypatch):
    from unittest.mock import Mock
    predictor = Mock()
    factory = Mock(return_value=predictor)
    legacy = Mock()
    monkeypatch.setattr(pe, "AgriPricePredictor", factory)
    monkeypatch.setattr(pe, "load_quantile_models", legacy)
    monkeypatch.setattr(pe.price_engine, "_loaded", False)
    monkeypatch.setattr(pe.price_engine, "_sota_predictor", None)
    pe.PriceEngine().load_models()
    pe.PriceEngine().load_models()
    factory.assert_called_once()
    predictor.load.assert_called_once()
    legacy.assert_called_once()


def test_fallback_forecast_is_non_crossing(monkeypatch):
    monkeypatch.setattr(pe.price_engine, "_sota_predictor", None)
    def unavailable(*args, **kwargs):
        raise pe.ModelUnavailable("test")
    monkeypatch.setattr(pe, "predict_quantiles", unavailable)
    points = pe.price_engine.predict_range("Lasalgaon APMC", "Onion", days=14)
    assert len(points) == 14
    assert all(p["p10_paise"] <= p["p50_paise"] <= p["p90_paise"] for p in points)
    assert all(p["source"] == "SYNTHETIC" for p in points)


@pytest.mark.asyncio
async def test_forecast_api_preserves_quantiles(monkeypatch):
    monkeypatch.setattr(pe.price_engine, "predict_range", lambda *args, **kwargs: [
        {"date": "2026-11-16", "p10_paise": 100000, "p50_paise": 120000, "p90_paise": 130000}
    ])
    app = FastAPI()
    app.include_router(ai.router)
    async with httpx.AsyncClient(transport=httpx.ASGITransport(app=app), base_url="http://test") as client:
        res = await client.get("/forecast?commodity=Onion&mandi=Lasalgaon")
    assert res.status_code == 200
    point = res.json()["points"][0]
    assert point["p10_paise_per_qtl"] <= point["p50_paise_per_qtl"] <= point["p90_paise_per_qtl"]


def test_window_response_preserves_economic_identities(monkeypatch):
    costs = CostBreakdown(1000, 1000, 1000, 1000, 1000, 5000)
    result = WindowResult(
        action="HOLD", hold_days=3, confidence="high", expected_gain_paise=200000,
        worst_case_paise=100000, refusal_reason=None, band_width_bps=1000,
        sell_now_net_paise_per_qtl=100000, hold_p50_net_paise_per_qtl=120000,
        hold_p10_net_paise_per_qtl=110000, costs=costs, explain_mr="धरा", explain_en="Hold",
    )
    monkeypatch.setattr(we, "decide", lambda **kwargs: result)
    monkeypatch.setattr(we.price_engine, "predict", lambda *args: {"p10_paise": 100000})
    response = we.compute_sale_window("Onion", "Lasalgaon", 1000, 100500, 20)
    assert response["hold_p50_net_paise_per_qtl"] == 120000
    assert response["hold_p10_net_paise_per_qtl"] == 110000
    assert response["expected_gain_paise"] == (120000 - response["sell_now_net_paise_per_qtl"]) * 10
    lines = response["itemised_costs"]
    assert sum(v for k, v in lines.items() if k != "total_paise_per_qtl") == lines["total_paise_per_qtl"]
    assert response["pledge_quote"]["loan_paise"] > 0


def test_pledge_only_when_gain_exceeds_interest():
    assert quote(10000000, 0, 14) is None
    result = quote(10000000, 100000, 14)
    assert result.loan_paise == 7000000
    assert result.interest_paise == 7000000 * 1200 * 14 // (10000 * 365)
    assert result.net_benefit_paise == 100000 - result.interest_paise


@pytest.mark.asyncio
async def test_missing_model_returns_no_advice_not_500(monkeypatch):
    from app.domain import window
    def unavailable(*args, **kwargs):
        raise pe.ModelUnavailable("missing")
    monkeypatch.setattr(window, "predict_quantiles", unavailable)
    app = FastAPI()
    app.include_router(ai.router)
    async with httpx.AsyncClient(transport=httpx.ASGITransport(app=app), base_url="http://test") as client:
        res = await client.post("/window/recommend", json={"commodity_id": "Onion", "qty_kg": 1000, "current_price_paise": 100000})
    assert res.status_code == 200
    assert res.json()["recommendation"] == "NO_ADVICE"
    assert res.json()["refusal_reason"] == "MODEL_UNAVAILABLE"


@pytest.mark.parametrize("method,payload", [
    ("speech_to_text", {"transcript": 123}),
    ("speech_to_text", []),
    ("text_to_speech", {"audios": {"bad": "shape"}}),
    ("text_to_speech", []),
])
@pytest.mark.asyncio
async def test_adapter_rejects_malformed_provider_response(monkeypatch, method, payload):
    from app.adapters import voice_adapter
    from app.config import settings
    monkeypatch.setattr(settings, "SARVAM_API_KEY", "test-key")
    real_client = httpx.AsyncClient
    transport = httpx.MockTransport(lambda request: httpx.Response(200, json=payload))
    monkeypatch.setattr(voice_adapter.httpx, "AsyncClient", lambda **kwargs: real_client(transport=transport, **kwargs))
    adapter = SarvamVoiceAdapter()
    with pytest.raises(VoiceEngineError):
        await getattr(adapter, method)(b"audio" if method == "speech_to_text" else "hello")


@pytest.mark.asyncio
async def test_api_validation_and_upload_errors():
    app = FastAPI()
    app.include_router(voice.router)
    app.dependency_overrides[get_voice_provider] = MockVoiceAdapter
    async with httpx.AsyncClient(transport=httpx.ASGITransport(app=app), base_url="http://test") as client:
        assert (await client.post("/narrate", json={})).status_code == 422
        assert (await client.post("/transcribe")).status_code == 422
