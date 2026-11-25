"""End-to-end router tests for `/api/v1/agent/chat`, `/voice-chat`, and `DELETE /session/{id}`."""
from __future__ import annotations

import json

import httpx
import pytest

from app.adapters.voice_adapter import MockVoiceAdapter
from app.agents.llm_client import ILLMClient, LLMResponse, LLMToolCall
from app.agents.memory import SessionMemoryStore
from app.config import settings
from app.database import get_db
from app.dependencies.auth import get_optional_user
from app.dependencies.voice import get_voice_provider
from app.engines.agent_engine import AgentEngine
from app.main import app
from app.models.agent_turn import AgentTurnLog
from app.routers import agent as agent_router
from app.services import agent_log_service


async def _no_db():
    yield None


@pytest.mark.asyncio
async def test_agent_chat_mock_mode_for_member1_and_3(monkeypatch):
    monkeypatch.setattr(settings, "AGENT_MOCK", True)
    app.dependency_overrides[get_db] = _no_db
    app.dependency_overrides[get_optional_user] = lambda: None
    try:
        async with httpx.AsyncClient(transport=httpx.ASGITransport(app=app), base_url="http://test") as client:
            r1 = await client.post(
                "/api/v1/agent/chat",
                json={"session_id": "s_mock", "message": "माझ्याकडे १० बोरी कांदा आहे, कधी विकू?", "locale": "mr"},
            )
            assert r1.status_code == 200
            body1 = r1.json()
            assert body1["intent_detected"] == "WINDOW"
            assert body1["cards"][0]["type"] == "WINDOW_VERDICT"
            assert body1["ui_action"]["target_screen"] == "S9_Verdict"

            r2 = await client.post(
                "/api/v1/agent/chat",
                json={"session_id": "s_mock", "message": "कांद्याचा भाव किती?", "locale": "mr"},
            )
            assert r2.status_code == 200
            assert r2.json()["cards"][0]["type"] == "PRICE_SNAPSHOT"

            r3 = await client.post(
                "/api/v1/agent/chat",
                json={"session_id": "s_mock", "message": "लॉट तयार करा", "locale": "mr"},
            )
            assert r3.status_code == 200
            assert r3.json()["cards"][0]["type"] == "LOT_DRAFT"
    finally:
        app.dependency_overrides.clear()


@pytest.mark.asyncio
async def test_agent_voice_chat_and_session_delete(monkeypatch, farmer, fake_redis):
    monkeypatch.setattr(settings, "AGENT_MOCK", False)
    monkeypatch.setenv("TRANSLATE_BACKEND", "stub")
    monkeypatch.setenv("TRANSLATE_PIVOT", "on")

    class OneShotLLM(ILLMClient):
        async def complete(self, messages, tools=None, **kwargs):
            return LLMResponse(
                content=None,
                tool_calls=[
                    LLMToolCall(
                        id="c1",
                        name="final_answer",
                        arguments={"reply_text": "Namaskar Ramesh, tell me how I can help.", "intent": "SMALLTALK"},
                        raw_arguments=json.dumps({"reply_text": "Namaskar Ramesh, tell me how I can help.", "intent": "SMALLTALK"}),
                    )
                ],
            )

    mem = SessionMemoryStore(fake_redis)
    engine = AgentEngine(llm_client=OneShotLLM(), memory=mem)

    app.dependency_overrides[get_db] = _no_db
    app.dependency_overrides[get_optional_user] = lambda: farmer
    app.dependency_overrides[agent_router.get_agent_engine] = lambda: engine
    app.dependency_overrides[agent_router.get_session_memory] = lambda: mem
    app.dependency_overrides[get_voice_provider] = MockVoiceAdapter
    try:
        async with httpx.AsyncClient(transport=httpx.ASGITransport(app=app), base_url="http://test") as client:
            # Missing audio -> 422
            bad = await client.post("/api/v1/agent/voice-chat", data={"session_id": "s_v1", "locale": "mr"})
            assert bad.status_code == 422

            # Valid voice upload -> audio_base64 WAV attached
            res = await client.post(
                "/api/v1/agent/voice-chat",
                data={
                    "session_id": "s_v1",
                    "locale": "mr",
                    "screen_context": json.dumps({"current_screen": "S4_Home"}),
                    "include_audio": "true",
                },
                files={"audio": ("clip.wav", b"RIFF0000WAVEfmt ", "audio/wav")},
            )
            assert res.status_code == 200
            body = res.json()
            assert body["intent_detected"] == "SMALLTALK"
            assert body["audio_base64"] is not None
            assert len(await mem.load_turns("s_v1")) == 1

            # Delete session memory
            del_res = await client.delete("/api/v1/agent/session/s_v1")
            assert del_res.status_code == 200
            assert del_res.json()["cleared"] is True
            assert await mem.load_turns("s_v1") == []
    finally:
        app.dependency_overrides.clear()


@pytest.mark.asyncio
async def test_turn_log_model_and_offline_resilience(monkeypatch):
    assert AgentTurnLog.__tablename__ == "agent_turns"

    class BrokenSession:
        async def __aenter__(self):
            raise RuntimeError("DB offline")

        async def __aexit__(self, *a):
            return False

    monkeypatch.setattr(agent_log_service, "async_session", lambda: BrokenSession())
    # Must never raise even if Postgres is down
    await agent_log_service.write_agent_turn_log(
        turn_id="t1",
        session_id="s1",
        original_text="कांदा",
        english_text="onion",
        english_reply="ok",
        reply_text="ठीक",
    )


def test_alembic_head_includes_agent_turns():
    from alembic.config import Config
    from alembic.script import ScriptDirectory

    cfg = Config("alembic.ini")
    script = ScriptDirectory.from_config(cfg)
    assert script.get_current_head() == "003_agent_turns"
    assert [r.revision for r in script.walk_revisions()] == [
        "003_agent_turns",
        "002_otp_and_reference",
        "001_ml_pledge",
        "2c47b09fff3c",
    ]


@pytest.mark.asyncio
async def test_compute_turn_metrics_and_get_metrics_endpoint():
    from types import SimpleNamespace

    sample_rows = [
        SimpleNamespace(
            turn_id="t1",
            session_id="s1",
            channel="text",
            locale="mr",
            intent_detected="PRICE",
            error_code=None,
            latency_ms=420,
            original_text="कांदा भाव काय?",
        ),
        SimpleNamespace(
            turn_id="t2",
            session_id="s1",
            channel="voice",
            locale="hi",
            intent_detected="WINDOW",
            error_code="NO_ADVICE",
            latency_ms=1380,
            original_text="कब बेचूं?",
        ),
        SimpleNamespace(
            turn_id="t3",
            session_id="s2",
            channel="text",
            locale="en",
            intent_detected="SMALLTALK",
            error_code="CHEMICAL_ADVICE_REFUSED",
            latency_ms=310,
            original_text="which spray for thrips?",
        ),
        SimpleNamespace(
            turn_id="t4",
            session_id="s3",
            channel="voice",
            locale="mr",
            intent_detected=None,
            error_code="LLM_UNAVAILABLE",
            latency_ms=2450,
            original_text="मदत करा",
        ),
    ]

    summary = agent_log_service.compute_turn_metrics(sample_rows)
    assert summary["total_turns"] == 4
    assert summary["refusal_count"] == 2
    assert summary["by_channel"] == {"text": 2, "voice": 2}
    assert summary["error_counts"] == {"NO_ADVICE": 1, "CHEMICAL_ADVICE_REFUSED": 1, "LLM_UNAVAILABLE": 1}
    assert summary["latency_ms"]["text"]["n"] == 2
    assert summary["latency_ms"]["voice"]["n"] == 2
    assert len(summary["recent_failures"]) == 1
    assert summary["recent_failures"][0]["error_code"] == "LLM_UNAVAILABLE"

    class FakeScalars:
        def all(self):
            return sample_rows

    class FakeExecResult:
        def scalars(self):
            return FakeScalars()

    class FakeMetricsDB:
        async def execute(self, stmt):
            return FakeExecResult()

    async def _fake_metrics_db():
        yield FakeMetricsDB()

    app.dependency_overrides[get_db] = _fake_metrics_db
    try:
        transport = httpx.ASGITransport(app=app)
        async with httpx.AsyncClient(transport=transport, base_url="http://test") as client:
            res = await client.get("/api/v1/agent/metrics?hours=24&limit=100")
            assert res.status_code == 200
            body = res.json()
            assert body["total_turns"] == 4
            assert body["refusal_count"] == 2
            assert body["by_intent"]["PRICE"] == 1
            assert body["latency_ms"]["overall"]["max_ms"] == 2450.0
    finally:
        app.dependency_overrides.clear()
