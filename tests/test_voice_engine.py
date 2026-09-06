"""
Voice engine — Sarvam STT proxy unit tests.

Verifies:
1. test_unconfigured_raises:      no SARVAM_API_KEY -> VoiceEngineError, configured False.
2. test_transcribe_returns_text:  mocked upstream 200 -> {transcript, language_code, request_id}.
3. test_upstream_error_surfaced:  mocked upstream 500 -> VoiceEngineError mentioning status.
4. test_transport_error_surfaced: network error -> VoiceEngineError mentioning unreachable.
5. test_upstream_empty_transcript: 200 with no transcript -> VoiceEngineError.

Pure engine tests: no database, no celery — mocking httpx.AsyncClient with a
MockTransport so nothing leaves the machine.
"""

from __future__ import annotations

import httpx
import pytest

from app.config import settings
from app.engines import voice_engine as ve


@pytest.fixture(autouse=True)
def _sarvam_key():
    """Give the engine a key for tests that need one; restore after."""
    old = settings.SARVAM_API_KEY
    settings.SARVAM_API_KEY = "test-key"
    yield
    settings.SARVAM_API_KEY = old


class _FakeAsyncClient(httpx.AsyncClient):
    """AsyncClient subclass that routes every request through a canned handler."""

    def __init__(self, handler, *args, **kwargs):  # noqa: ANN002
        kwargs["transport"] = httpx.MockTransport(handler)
        super().__init__(*args, **kwargs)


def test_unconfigured_raises():
    settings.SARVAM_API_KEY = ""
    eng = ve.VoiceEngine()
    assert eng.configured is False
    with pytest.raises(ve.VoiceEngineError, match="not configured"):
        # speech_to_text is async; we only need the sync guard check, so run it
        import asyncio
        asyncio.run(eng.speech_to_text(b"x"))


def _patch_client(monkeypatch, handler):
    def make(*args, **kwargs):
        return _FakeAsyncClient(handler, *args, **kwargs)

    monkeypatch.setattr(ve.httpx, "AsyncClient", make)


@pytest.mark.asyncio
async def test_transcribe_returns_text(monkeypatch):
    def handler(request: httpx.Request) -> httpx.Response:
        assert request.headers.get("api-subscription-key") == "test-key"
        body = request.read()
        assert b"saaras:v3" in body
        assert b"mr-IN" in body
        return httpx.Response(
            200,
            json={
                "request_id": "req_123",
                "transcript": "रामभाऊ पाटील",
                "language_code": "mr-IN",
            },
        )

    _patch_client(monkeypatch, handler)
    eng = ve.VoiceEngine()
    res = await eng.speech_to_text(b"\x00fakeaudio", language_code="mr-IN")
    assert res["transcript"] == "रामभाऊ पाटील"
    assert res["language_code"] == "mr-IN"
    assert res["request_id"] == "req_123"


@pytest.mark.asyncio
async def test_upstream_error_surfaced(monkeypatch):
    def handler(request: httpx.Request) -> httpx.Response:
        return httpx.Response(500, json={"error": {"message": "boom"}})

    _patch_client(monkeypatch, handler)
    eng = ve.VoiceEngine()
    with pytest.raises(ve.VoiceEngineError, match="500"):
        await eng.speech_to_text(b"x")


@pytest.mark.asyncio
async def test_transport_error_surfaced(monkeypatch):
    def handler(request: httpx.Request) -> httpx.Response:
        raise httpx.ConnectError("connection refused")

    _patch_client(monkeypatch, handler)
    eng = ve.VoiceEngine()
    with pytest.raises(ve.VoiceEngineError, match="unreachable"):
        await eng.speech_to_text(b"x")


@pytest.mark.asyncio
async def test_upstream_empty_transcript(monkeypatch):
    def handler(request: httpx.Request) -> httpx.Response:
        return httpx.Response(200, json={"request_id": "req_1", "transcript": "  "})

    _patch_client(monkeypatch, handler)
    eng = ve.VoiceEngine()
    with pytest.raises(ve.VoiceEngineError, match="empty transcript"):
        await eng.speech_to_text(b"x")
