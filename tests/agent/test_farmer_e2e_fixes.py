"""Regression tests for Farmer E2E fixes (runs cleanly offline without Postgres)."""
from __future__ import annotations

import io
from datetime import datetime, timezone
from types import SimpleNamespace

import httpx
import openai
import pytest
from httpx import ASGITransport, AsyncClient
from PIL import Image

from app.agents.llm_client import OpenAICompatibleLLMClient, ProviderConfig
from app.agents.response_builder import build_card_fallback_reply
from app.agents.tool_bridge import execute_agent_tool
from app.agents.tools import ToolContext
from app.database import get_db
from app.dependencies.auth import get_current_user
from app.engines.agent_engine import AgentEngine
from app.main import app
from app.models.chat import ThreadMessage
from app.models.fpo import FPO
from app.models.lot import Lot
from app.models.user import User
from app.nlp.messages import MESSAGES
from app.nlp.translate import TranslationUnavailable
from app.rag.embedder import LexicalEmbedder, make_embedder
from app.routers import chats as chats_router, lots as lots_router
from app.schemas.agent import AgentCard


@pytest.mark.asyncio
async def test_llm_client_fails_over_on_402_insufficient_quota():
    seen: list[str] = []

    class FakeCompletions:
        def __init__(self, provider: str):
            self.provider = provider

        async def create(self, **kwargs):
            seen.append(self.provider)
            if self.provider == "sarvam":
                req = httpx.Request("POST", "https://api.sarvam.ai/v1/chat/completions")
                raise openai.APIStatusError(
                    "No credits available",
                    response=httpx.Response(402, request=req),
                    body={"error": {"code": "insufficient_quota_error"}},
                )
            tc = SimpleNamespace(
                id="call_ok",
                function=SimpleNamespace(name="final_answer", arguments='{"reply_text": "Onion is Rs 2150.", "intent": "PRICE"}'),
            )
            return SimpleNamespace(
                choices=[SimpleNamespace(message=SimpleNamespace(content=None, tool_calls=[tc]))],
                usage=SimpleNamespace(prompt_tokens=1, completion_tokens=1, total_tokens=2),
            )

    client = OpenAICompatibleLLMClient(
        [
            ProviderConfig("sarvam", "https://api.sarvam.ai/v1", "k1", "sarvam-105b"),
            ProviderConfig("gemini", "https://generativelanguage.googleapis.com/v1beta/openai/", "k2", "gemini-2.5-flash"),
        ],
        client_factory=lambda cfg, _t: SimpleNamespace(chat=SimpleNamespace(completions=FakeCompletions(cfg.name))),
    )
    resp = await client.complete([{"role": "user", "content": "onion price"}])
    assert seen == ["sarvam", "gemini"]
    assert resp.provider == "gemini"


def test_fallback_reply_mentions_card_only_when_card_exists():
    empty_msg = build_card_fallback_reply([], "en")
    assert empty_msg == MESSAGES["FALLBACK"]["en"]
    assert "card below" not in empty_msg.lower()

    card_msg = build_card_fallback_reply(
        [AgentCard(type="PRICE_SNAPSHOT", data={"commodity": "Onion", "mandi": "Lasalgaon APMC", "modal_paise_per_qtl": 215000})],
        "en",
    )
    assert MESSAGES["FALLBACK"]["en"] in card_msg
    assert "card below" in card_msg.lower()
    assert "2150" in card_msg


@pytest.mark.asyncio
async def test_agent_engine_handles_text_when_sarvam_translate_fails(monkeypatch):
    from app.engines import agent_engine as eng_mod

    class FakeMem:
        async def load_turns(self, sid):
            return []

        async def append_turn(self, *a, **k):
            return None

    async def fail_translate(**kwargs):
        raise TranslationUnavailable("402 quota")

    monkeypatch.setattr(eng_mod, "to_english", fail_translate)

    class OkLLM:
        async def complete(self, messages, tools=None, **kwargs):
            from app.agents.llm_client import LLMResponse, LLMToolCall

            return LLMResponse(
                content=None,
                tool_calls=[
                    LLMToolCall(
                        "c1",
                        "final_answer",
                        {"reply_text": "सध्या कांद्याचा भाव पाहता येतो.", "intent": "SMALLTALK"},
                    )
                ],
            )

    engine_inst = AgentEngine(llm_client=OkLLM(), memory=FakeMem())  # type: ignore[arg-type]
    resp = await engine_inst.run_turn(
        db=None,
        user=None,
        session_id="sess_tr_degrade",
        locale="mr",
        text="कांदा भाव काय आहे?",
        persist_log=False,
    )
    assert resp.error_code is None
    assert "कांद्याचा" in resp.reply_text


@pytest.mark.asyncio
async def test_mandi_hint_applies_to_create_lot_draft_even_when_omitted(farmer):
    res = await execute_agent_tool(
        "create_lot_draft",
        ToolContext(db=None, user=farmer, locale="en", screen={}),
        {"commodity": "onion", "quantity": 1000, "unit": "kg"},
        hints={"commodity": "cmd_onion", "mandi": "mkt_lasalgaon", "quantity_kg": 1000},
    )
    assert res.envelope.data["market"]["slug"] == "mkt_lasalgaon"
    assert res.envelope.card["data"]["commodity_id"] == "cmd_onion"
    assert res.envelope.card["data"]["market_id"] == "mkt_lasalgaon"


@pytest.mark.asyncio
async def test_portfolio_uses_canonical_lot_status_enum(farmer):
    class FakeResult:
        def __init__(self, rows):
            self._rows = rows

        def scalars(self):
            return SimpleNamespace(all=lambda: self._rows)

    class FakeDB:
        def __init__(self):
            self.i = 0

        async def execute(self, _stmt):
            self.i += 1
            if self.i == 1:
                return FakeResult([
                    SimpleNamespace(id=1, commodity_id=1, market_id=1, quantity_qtl=10, expected_price_paise=220000, grade="A", status="active"),
                    SimpleNamespace(id=2, commodity_id=1, market_id=1, quantity_qtl=10, expected_price_paise=220000, grade="B", status="locked"),
                ])
            return FakeResult([])

    res = await execute_agent_tool("get_farmer_portfolio", ToolContext(db=FakeDB(), user=farmer, locale="en"), {})
    assert res.envelope.ok
    assert [l["status"] for l in res.envelope.data["lots"]] == ["LISTED", "OFFERED"]
    assert res.envelope.data["summary"]["active_lot_count"] == 1


def test_make_embedder_falls_back_gracefully_without_flagembedding(monkeypatch):
    import builtins

    real_import = builtins.__import__

    def fake_import(name, *args, **kwargs):
        if name == "FlagEmbedding":
            raise ModuleNotFoundError("FlagEmbedding missing")
        return real_import(name, *args, **kwargs)

    monkeypatch.setattr(builtins, "__import__", fake_import)
    emb = make_embedder("bge-m3")
    assert isinstance(emb, LexicalEmbedder)


@pytest.mark.asyncio
async def test_photo_upload_get_pool_and_thread_chat_roundtrip(tmp_path, monkeypatch, farmer):
    async def noop_s3_upload(*a, **k):
        raise RuntimeError("offline")

    async def noop_s3_download(*a, **k):
        return None

    monkeypatch.setattr(lots_router, "_LOCAL_UPLOAD_ROOT", tmp_path)
    monkeypatch.setattr(lots_router.s3_utils, "upload_file", noop_s3_upload)
    monkeypatch.setattr(lots_router.s3_utils, "download_file", noop_s3_download)
    monkeypatch.setattr(chats_router, "_TABLE_READY", True)

    farmer_user = SimpleNamespace(id=1, role="FARMER", name="Ramesh Patil", district_id=1)
    lot_obj = SimpleNamespace(
        id=7,
        farmer_id=1,
        fpo_id=1,
        commodity_id=1,
        market_id=1,
        quantity_qtl=20,
        expected_price_paise=220000,
        grade="A",
        self_assay_answers={"size_uniform": 3, "colour_uniform": 3, "damage_pct": 2, "sprouting": 3, "moisture_feel": 3, "foreign_matter": 3},
        status="active",
        image_url=None,
    )
    lot_obj2 = SimpleNamespace(
        id=8,
        farmer_id=2,
        fpo_id=1,
        commodity_id=1,
        market_id=1,
        quantity_qtl=10,
        expected_price_paise=220000,
        grade="B",
        self_assay_answers=None,
        status="active",
        image_url=None,
    )
    fpo_obj = SimpleNamespace(id=1, name="Niphad Kanda Utpadak FPO")
    owner2 = SimpleNamespace(id=2, name="Sunita Pawar")
    stored_msgs: list[ThreadMessage] = []

    class FakeSession:
        async def get(self, model, pk):
            if model is Lot:
                return {7: lot_obj, 8: lot_obj2}.get(pk)
            if model is FPO:
                return fpo_obj if pk == 1 else None
            if model is User:
                return {1: farmer_user, 2: owner2}.get(pk)
            return None

        async def execute(self, stmt):
            sql = str(stmt)
            if "batch_lot_members" in sql:
                return SimpleNamespace(scalars=lambda: SimpleNamespace(all=lambda: []))
            if "FROM lots" in sql:
                return SimpleNamespace(scalars=lambda: SimpleNamespace(all=lambda: [lot_obj, lot_obj2]))
            if "FROM users" in sql:
                return SimpleNamespace(scalars=lambda: SimpleNamespace(all=lambda: [farmer_user, owner2]))
            if "FROM offers" in sql:
                return SimpleNamespace(first=lambda: None)
            if "FROM thread_messages" in sql:
                return SimpleNamespace(scalars=lambda: SimpleNamespace(all=lambda: list(stored_msgs)))
            return SimpleNamespace(scalars=lambda: SimpleNamespace(all=lambda: []))

        def add(self, obj):
            if getattr(obj, "id", None) is None:
                obj.id = len(stored_msgs) + 1
            if getattr(obj, "created_at", None) is None:
                obj.created_at = datetime.now(timezone.utc)
            stored_msgs.append(obj)

        async def flush(self):
            return None

        async def refresh(self, _obj):
            return None

        async def commit(self):
            return None

    fake_db = FakeSession()

    async def override_db():
        yield fake_db

    app.dependency_overrides[get_db] = override_db
    app.dependency_overrides[get_current_user] = lambda: farmer_user

    img_buf = io.BytesIO()
    Image.new("RGB", (32, 32), color=(200, 60, 40)).save(img_buf, format="JPEG")

    try:
        async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as client:
            up = await client.post(
                "/api/v1/lots/7/photo",
                files={"file": ("crop.jpg", img_buf.getvalue(), "image/jpeg")},
            )
            assert up.status_code == 200
            assert up.json()["photo_path"] == "/api/v1/lots/7/photo"
            assert lot_obj.image_url == "/api/v1/lots/7/photo"

            fetched = await client.get("/api/v1/lots/7/photo")
            assert fetched.status_code == 200
            assert fetched.headers["content-type"].startswith("image/jpeg")

            pool = await client.get("/api/v1/pools/fpo_1")
            assert pool.status_code == 200
            pdata = pool.json()
            assert pdata["fpo"]["name"] == "Niphad Kanda Utpadak FPO"
            assert pdata["total_qty_kg"] == 3000
            assert sum(m["share_bps"] for m in pdata["members"]) == 10000

            pool_missing = await client.get("/api/v1/pools/999999")
            assert pool_missing.status_code == 404

            sent = await client.post("/api/v1/chats/lot_7/messages", json={"text": "Kanda ekdum kadak aahe"})
            assert sent.status_code == 201
            msg = sent.json()
            assert msg["text"] == "Kanda ekdum kadak aahe"
            assert msg["is_me"] is True

            listed = await client.get("/api/v1/chats/lot_7/messages")
            assert listed.status_code == 200
            assert listed.json()[0]["text"] == "Kanda ekdum kadak aahe"
    finally:
        app.dependency_overrides.clear()


@pytest.mark.asyncio
async def test_stub_translate_with_pivot_off_preserves_farmer_text_and_hints(monkeypatch):
    from app.nlp import translate as T

    monkeypatch.setenv("TRANSLATE_BACKEND", "stub")
    monkeypatch.setenv("TRANSLATE_PIVOT", "off")
    res = await T.to_english(text="आज पुण्यात टोमॅटोचा भाव काय आहे?", locale_hint="mr")
    assert res.original == "आज पुण्यात टोमॅटोचा भाव काय आहे?"
    assert res.english == res.original
    assert res.source_lang == "mr"
    assert res.hints.get("commodity") == "cmd_tomato"


def test_groq_fallback_models_expands_provider_chain_when_set(monkeypatch):
    from app.agents.llm_client import build_provider_chain

    monkeypatch.setenv("LLM_PROVIDER", "groq")
    monkeypatch.setenv("GROQ_API_KEY", "gsk_test")
    monkeypatch.setenv("GROQ_FALLBACK_MODELS", "openai/gpt-oss-20b,qwen/qwen3.8-27b")
    monkeypatch.setenv("GEMINI_API_KEY", "")
    monkeypatch.setenv("SARVAM_API_KEY", "")
    monkeypatch.setenv("OPENAI_API_KEY", "")
    chain = build_provider_chain()
    assert [c.model for c in chain] == [
        "openai/gpt-oss-120b",
        "openai/gpt-oss-20b",
        "qwen/qwen3.8-27b",
    ]


@pytest.mark.asyncio
async def test_llm_client_recovers_and_fails_over_on_400_tool_use_failed():
    import httpx
    import openai
    from types import SimpleNamespace
    from app.agents.llm_client import OpenAICompatibleLLMClient, ProviderConfig

    seen = []

    class FakeCompletions:
        def __init__(self, name: str):
            self.name = name

        async def create(self, **kwargs):
            seen.append((self.name, kwargs.get("tool_choice")))
            req = httpx.Request("POST", "https://api.groq.com/openai/v1/chat/completions")
            resp = httpx.Response(400, request=req)
            if self.name == "groq":
                raise openai.APIStatusError(
                    "Error code: 400 - {'error': {'code': 'tool_use_failed', 'message': 'Tool choice is required'}}",
                    response=resp,
                    body={"error": {"code": "tool_use_failed"}},
                )
            tc = SimpleNamespace(
                id="c1",
                function=SimpleNamespace(name="final_answer", arguments='{"reply_text": "Ok", "intent": "SMALLTALK"}'),
            )
            return SimpleNamespace(
                choices=[SimpleNamespace(message=SimpleNamespace(content=None, tool_calls=[tc]))],
                usage=SimpleNamespace(prompt_tokens=10, completion_tokens=5, total_tokens=15),
            )

    client = OpenAICompatibleLLMClient(
        providers=[
            ProviderConfig("groq", "https://api.groq.com/openai/v1", "k1", "openai/gpt-oss-120b"),
            ProviderConfig("groq:qwen", "https://api.groq.com/openai/v1", "k1", "qwen/qwen3.8-27b"),
        ],
        client_factory=lambda cfg, _: SimpleNamespace(chat=SimpleNamespace(completions=FakeCompletions(cfg.name))),
    )
    res = await client.complete(
        [{"role": "user", "content": "hi"}],
        tools=[{"type": "function", "function": {"name": "final_answer"}}],
        tool_choice="required",
    )
    assert res.provider == "groq:qwen"
    assert ("groq", "required") in seen and ("groq", "auto") in seen and ("groq:qwen", "required") in seen


@pytest.mark.asyncio
async def test_voice_transcribe_cached_sarvam_falls_back_to_groq_whisper(monkeypatch, tmp_path):
    from fastapi import FastAPI
    import httpx
    from unittest.mock import AsyncMock
    from app.adapters.cached_voice_decorator import CachedVoiceDecorator
    from app.adapters.voice_adapter import SarvamVoiceAdapter
    from app.adapters.voice_provider import VoiceEngineError
    from app.dependencies.voice import get_voice_provider
    from app.routers import voice
    from app.schemas.voice import TranscribeResponse

    adapter = SarvamVoiceAdapter()
    monkeypatch.setattr(SarvamVoiceAdapter, "configured", property(lambda self: True))
    monkeypatch.setattr(adapter, "speech_to_text", AsyncMock(side_effect=VoiceEngineError("HTTP 402")))
    decorated = CachedVoiceDecorator(adapter, tmp_path)

    async def fake_groq(raw, *, filename, locale):
        return TranscribeResponse(transcript="lasalgaon onion rate", language_code="en-IN")

    monkeypatch.setattr(voice, "_groq_whisper_transcribe", fake_groq)
    app = FastAPI()
    app.include_router(voice.router, prefix="/api/v1/voice")
    app.dependency_overrides[get_voice_provider] = lambda: decorated
    async with httpx.AsyncClient(transport=httpx.ASGITransport(app=app), base_url="http://test") as client:
        res = await client.post("/api/v1/voice/transcribe", files={"file": ("a.wav", b"RIFF0000WAVE", "audio/wav")}, data={"locale": "en"})
    assert res.status_code == 200
    assert res.json()["transcript"] == "lasalgaon onion rate"


