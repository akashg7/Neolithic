"""Tests for tool_bridge (hint-wins, unit checks, RAG/portfolio/navigation) and Redis memory."""
from __future__ import annotations

import pytest

from app.agents.context import build_context_messages, build_farmer_profile_block
from app.agents.memory import SessionMemoryStore
from app.agents.tool_bridge import agent_tool_schemas, execute_agent_tool
from app.agents.tools import ToolContext
from app.agents.tools import decision as decision_mod
from app.contracts import RetrievedChunk
from app.schemas.agent import ScreenContext
from app.services import price_service


def _ctx(user=None, locale="mr", db=None, **screen):
    return ToolContext(db=db, user=user, locale=locale, screen=screen)


def test_agent_tool_schemas_are_coarse_and_safe():
    schemas = agent_tool_schemas()
    names = [s["function"]["name"] for s in schemas]
    assert names == [
        "compute_sale_window",
        "get_price_forecast",
        "calculate_grade",
        "create_lot_draft",
        "get_farmer_portfolio",
        "search_agri_knowledge",
        "navigate_screen",
        "final_answer",
    ]
    # No user_id/farmer_id parameters exposed to the LLM
    for s in schemas:
        props = s["function"]["parameters"].get("properties", {})
        assert not {"user_id", "farmer_id", "buyer_id"} & set(props)


@pytest.mark.asyncio
async def test_hint_wins_over_wrong_model_args(monkeypatch, farmer):
    captured = {}

    async def fake_sale_window(db, **kw):
        captured.update(kw)
        return {
            "action": "HOLD",
            "recommendation": "HOLD",
            "confidence": "HIGH",
            "hold_days": 5,
            "band_width_bps": 1200,
            "expected_gain_paise": 185000,
            "worst_case_paise": 40000,
            "sell_now_net_paise_per_qtl": 205000,
            "itemised_costs": {"total_paise_per_qtl": 9000},
            "pledge_quote": None,
            "refusal_reason": None,
            "explain_mr": "थांबा",
            "explain_en": "Hold",
            "data_source": "AGMARKNET_ML",
            "inputs": {
                "commodity": {"slug": "cmd_onion", "name": "Onion", "name_mr": "कांदा", "id": 1},
                "market": {"slug": "mkt_lasalgaon", "name": "Lasalgaon APMC", "name_mr": "लासलगाव", "id": 1},
                "quantity_kg": kw["quantity_kg"],
                "transport_included": True,
                "spot_price_source": "AGMARKNET",
                "spot_price_date": "2026-11-24",
            },
        }

    monkeypatch.setattr(decision_mod, "sale_window", fake_sale_window)

    # Model gets commodity, mandi, and quantity all wrong; original hints win!
    out = await execute_agent_tool(
        "compute_sale_window",
        _ctx(user=farmer),
        {"commodity": "tomato", "mandi": "pune", "quantity": 5, "unit": "kg"},
        hints={"commodity": "cmd_onion", "mandi": "mkt_lasalgaon", "quantity_kg": 1000},
    )
    assert out.envelope.ok
    assert captured["commodity_ref"] == 1
    assert captured["market_ref"] == 1
    assert captured["quantity_kg"] == 1000
    assert out.envelope.card["type"] == "WINDOW_VERDICT"
    assert out.ui_action["target_screen"] == "S9_Verdict"


@pytest.mark.asyncio
async def test_variable_unit_asks_farmer_never_guesses(farmer):
    # Via hint
    res1 = await execute_agent_tool(
        "compute_sale_window",
        _ctx(user=farmer),
        {"commodity": "onion", "mandi": "lasalgaon", "quantity": 10, "unit": "khandi"},
        hints={"unit_unknown": "khandi"},
    )
    assert not res1.envelope.ok
    assert "NEEDS_INPUT" in (res1.envelope.error or "")

    # Via unit parser when no hint exists (goni is variable_size in app.nlp.units)
    res2 = await execute_agent_tool(
        "create_lot_draft",
        _ctx(user=farmer),
        {"commodity": "onion", "quantity": 10, "unit": "goni"},
        hints={},
    )
    assert not res2.envelope.ok
    assert "NEEDS_INPUT" in (res2.envelope.error or "")


@pytest.mark.asyncio
async def test_get_price_forecast_combines_snapshot_and_model(monkeypatch):
    snap = {
        "obs_date": "2026-11-24",
        "min_paise_per_qtl": 180000,
        "max_paise_per_qtl": 240000,
        "modal_paise_per_qtl": 215000,
        "arrivals_qtl": 9500,
        "source": "AGMARKNET",
        "prev_obs_date": "2026-11-17",
        "prev_modal_paise_per_qtl": 200000,
        "change_paise_per_qtl": 15000,
        "change_bps": 750,
    }

    async def fake_snap(*a, **k):
        return dict(snap)

    async def fake_latest(*a, **k):
        return dict(snap)

    pts = [
        {"target_date": "2026-11-25", "p10_paise_per_qtl": 195000, "p50_paise_per_qtl": 220000, "p90_paise_per_qtl": 245000}
    ]
    monkeypatch.setattr(price_service, "mandi_snapshot", fake_snap)
    monkeypatch.setattr(price_service, "latest_price", fake_latest)
    monkeypatch.setattr(price_service, "forecast", lambda *a, **k: {"points": pts, "source": "AGMARKNET_SOTA", "is_model": True})

    out = await execute_agent_tool("get_price_forecast", _ctx(), {"commodity": "onion", "mandi": "lasalgaon"})
    assert out.envelope.ok
    assert out.envelope.card["type"] == "PRICE_SNAPSHOT"
    assert out.envelope.data["snapshot"]["modal_paise_per_qtl"] == 215000
    assert out.envelope.data["forecast"]["summary"]["peak_p50_paise_per_qtl"] == 220000


@pytest.mark.asyncio
async def test_calculate_grade_accepts_nested_assay_and_flat_fields():
    partial = await execute_agent_tool("calculate_grade", _ctx(locale="en"), {"assay": {"size_uniform": 3}})
    assert partial.envelope.ok
    assert partial.envelope.data["complete"] is False
    assert partial.envelope.data["next_question"]["field"] == "colour_uniform"

    full = await execute_agent_tool(
        "calculate_grade",
        _ctx(locale="en"),
        {"assay": {"size_uniform": 3, "colour_uniform": 3, "damage_pct": 2, "sprouting": 3, "moisture_feel": 3, "foreign_matter": 3}},
    )
    assert full.envelope.ok
    assert full.envelope.data["grade"] == "A"


@pytest.mark.asyncio
async def test_search_agri_knowledge_and_navigation(monkeypatch):
    chunks = [
        RetrievedChunk(
            chunk_id="wdra_01",
            text="WDRA e-NWR pledge loan offers up to 75% LTV.",
            source_doc="schemes_finance/wdra.md",
            section_title="WDRA Pledge Loan",
            category="schemes_finance",
            language="en",
            score=0.92,
        )
    ]

    async def fake_search(query, locale, category=None, crop=None, k=4):
        return chunks

    from app.agents.tools import knowledge as knowledge_mod

    monkeypatch.setattr(knowledge_mod, "rag_search", fake_search)

    rag_res = await execute_agent_tool("search_agri_knowledge", _ctx(), {"query": "warehouse pledge loan"})
    assert rag_res.envelope.ok
    assert rag_res.envelope.card["type"] == "RAG_CITATION"
    assert rag_res.citations[0]["chunk_id"] == "wdra_01"

    nav_ok = await execute_agent_tool("navigate_screen", _ctx(locale="en"), {"target_screen": "profile"})
    assert nav_ok.envelope.ok
    assert nav_ok.ui_action["target_screen"] == "S35_FarmerProfile"

    nav_bad = await execute_agent_tool("navigate_screen", _ctx(), {"target_screen": "S99_AdminHack"})
    assert not nav_bad.envelope.ok


@pytest.mark.asyncio
async def test_portfolio_requires_login():
    res = await execute_agent_tool("get_farmer_portfolio", _ctx(user=None), {})
    assert not res.envelope.ok
    assert "NEEDS_LOGIN" in (res.envelope.error or "")


@pytest.mark.asyncio
async def test_portfolio_queries_user_lots_offers_transactions(farmer):
    from types import SimpleNamespace

    class FakeResult:
        def __init__(self, rows):
            self._rows = rows

        def scalars(self):
            return SimpleNamespace(all=lambda: self._rows)

    class FakeDB:
        def __init__(self):
            self.calls = 0

        async def execute(self, stmt):
            self.calls += 1
            if self.calls == 1:
                return FakeResult([
                    SimpleNamespace(id=10, commodity_id=1, market_id=1, quantity_qtl=10, expected_price_paise=220000, grade="A", status="active")
                ])
            if self.calls == 2:
                return FakeResult([
                    SimpleNamespace(id=20, price_paise_per_qtl=215000, qty_kg=1000, round=1, initiator="BUYER", status="OPEN")
                ])
            return FakeResult([
                SimpleNamespace(id=30, offer_id=20, amount_paise=2150000, status="DEPOSIT_HELD")
            ])

    res = await execute_agent_tool("get_farmer_portfolio", _ctx(user=farmer, db=FakeDB()), {})
    assert res.envelope.ok
    assert res.envelope.data["summary"]["active_lot_count"] == 1
    assert res.envelope.data["summary"]["open_offer_count"] == 1
    assert res.envelope.data["summary"]["transaction_count"] == 1
    assert res.envelope.data["active_lots"][0]["commodity"] == "Onion"


@pytest.mark.asyncio
async def test_bakeoff_loop_hook(monkeypatch):
    import json as _json
    from pathlib import Path
    from types import SimpleNamespace
    from app.contracts import EvalRow
    from eval import bakeoff as B

    row = EvalRow(**_json.loads((Path(B.ROOT) / "eval/data/bakeoff_40.jsonl").read_text("utf-8").splitlines()[4]))
    cand = {"name": "mock", "model": "openai/gpt-oss-120b", "base_url": "https://api.groq.com/openai/v1", "api_key_env": "GROQ_API_KEY"}
    monkeypatch.setenv("GROQ_API_KEY", "k")

    async def fake_complete(self, messages, tools=None, **kw):
        from app.agents.llm_client import LLMResponse, LLMToolCall

        step = sum(1 for m in messages if m.get("role") == "tool")
        if step == 0:
            return LLMResponse(
                content=None,
                tool_calls=[LLMToolCall("c1", "compute_sale_window", {"commodity": "onion", "mandi": "lasalgaon", "quantity": 20, "unit": "bori"}, "{}")],
                latency_ms=42.0,
            )
        return LLMResponse(
            content=None,
            tool_calls=[LLMToolCall("c2", "final_answer", {"reply_text": "Hold 5 days.", "intent": "WINDOW"}, "{}")],
            latency_ms=31.0,
        )

    from app.agents import llm_client

    monkeypatch.setattr(llm_client.OpenAICompatibleLLMClient, "complete", fake_complete)
    turn = await B.run_turn_agent_loop(cand, row)
    assert turn.tool_ok and turn.args_ok_hints and turn.calls == 2


@pytest.mark.asyncio
async def test_redis_memory_keeps_last_8_turns_and_ttl(fake_redis):
    mem = SessionMemoryStore(fake_redis, ttl_seconds=1800, max_turns=8)
    for i in range(10):
        await mem.append_turn(
            "sess_1",
            user_text=f"turn {i}",
            assistant_text=f"reply {i}",
            intent="PRICE",
            tool_summaries=[f"[get_price_forecast: modal=215000]"],
        )

    assert fake_redis.ttls["agent:mem:sess_1"] == 1800
    turns = await mem.load_turns("sess_1")
    assert len(turns) == 8
    assert turns[0].user == "turn 2"
    assert turns[-1].user == "turn 9"

    assert await mem.clear_session("sess_1") is True
    assert await mem.load_turns("sess_1") == []


@pytest.mark.asyncio
async def test_context_builder_orders_prefix_for_prompt_cache(farmer, fake_redis):
    mem = SessionMemoryStore(fake_redis)
    await mem.append_turn("sess_p", user_text="Hello", assistant_text="Hi Ramesh")
    profile = await build_farmer_profile_block(None, farmer)
    assert "Ramesh Patil" in profile
    assert "FARMER" in profile

    msgs = build_context_messages(
        profile_block=profile,
        history_turns=await mem.load_turns("sess_p"),
        screen_context=ScreenContext(current_screen="S4_Home", active_commodity_id="cmd_onion"),
        model_input_text="Should I sell now?",
        hints={"commodity": "cmd_onion", "quantity_kg": 1000},
    )
    assert msgs[0]["role"] == "system"
    assert msgs[1]["role"] == "system" and "Ramesh Patil" in msgs[1]["content"]
    assert msgs[2]["role"] == "user" and msgs[2]["content"] == "Hello"
    assert msgs[3]["role"] == "assistant"
    assert msgs[4]["role"] == "user" and "Hints from the farmer's original words: commodity=cmd_onion, quantity_kg=1000" in msgs[4]["content"]


@pytest.mark.asyncio
async def test_card_enrichments_for_frontend_compatibility(monkeypatch, farmer):
    # 1. WINDOW_VERDICT carries rounded uncertainty_pct = band_width_bps / 100
    async def fake_sale_window(db, **kw):
        return {
            "action": "NO_ADVICE",
            "recommendation": "NO_ADVICE",
            "confidence": "LOW",
            "hold_days": None,
            "band_width_bps": 4200,
            "expected_gain_paise": 0,
            "worst_case_paise": 0,
            "sell_now_net_paise_per_qtl": 205000,
            "itemised_costs": {"total_paise_per_qtl": 9000},
            "pledge_quote": None,
            "refusal_reason": "Volatility too high",
            "explain_mr": "सल्ला नाही",
            "explain_en": "No advice",
            "data_source": "AGMARKNET_ML",
            "inputs": {
                "commodity": {"slug": "cmd_onion", "name": "Onion", "name_mr": "कांदा", "id": 1},
                "market": {"slug": "mkt_lasalgaon", "name": "Lasalgaon APMC", "name_mr": "लासलगाव", "id": 1},
                "quantity_kg": kw["quantity_kg"],
                "transport_included": True,
                "spot_price_source": "AGMARKNET",
                "spot_price_date": "2026-11-24",
            },
        }

    monkeypatch.setattr(decision_mod, "sale_window", fake_sale_window)
    w_res = await execute_agent_tool(
        "compute_sale_window",
        _ctx(user=farmer, db=None),
        {"commodity": "onion", "mandi": "lasalgaon", "quantity": 10, "unit": "qtl"},
    )
    assert w_res.envelope.card["type"] == "WINDOW_VERDICT"
    assert w_res.envelope.card["data"]["uncertainty_pct"] == 42

    # 2. PRICE_SNAPSHOT carries modal_price_paise_per_qtl & 7-day series_paise_per_qtl
    snap = {
        "commodity": {"id": 1, "name": "Onion"},
        "market": {"id": 1, "name": "Lasalgaon APMC"},
        "obs_date": "2026-04-14",
        "min_paise_per_qtl": 200000,
        "max_paise_per_qtl": 230000,
        "modal_paise_per_qtl": 215000,
        "arrivals_qtl": 1200,
        "prev_obs_date": "2026-04-07",
        "prev_modal_paise_per_qtl": 210000,
        "change_paise_per_qtl": 5000,
        "change_bps": 238,
        "source": "AGMARKNET",
    }

    async def fake_snap(*a, **kw):
        return dict(snap)

    async def fake_latest_price(*a, **kw):
        return dict(snap)

    async def fake_price_series(db, comm_id, mkt_id, days=14):
        return {"points": [{"modal_paise_per_qtl": 205000 + i * 1000} for i in range(10)]}

    pts = [{"target_date": "2026-04-15", "p10_paise_per_qtl": 195000, "p50_paise_per_qtl": 220000, "p90_paise_per_qtl": 245000}]
    monkeypatch.setattr(price_service, "mandi_snapshot", fake_snap)
    monkeypatch.setattr(price_service, "latest_price", fake_latest_price)
    monkeypatch.setattr(price_service, "price_series", fake_price_series)
    monkeypatch.setattr(price_service, "forecast", lambda *a, **k: {"points": pts, "source": "AGMARKNET_SOTA", "is_model": True})

    p_no_db = await execute_agent_tool(
        "get_price_forecast",
        _ctx(user=farmer, db=None),
        {"commodity": "onion", "mandi": "lasalgaon"},
    )
    assert p_no_db.envelope.card["data"]["modal_price_paise_per_qtl"] == 215000
    assert p_no_db.envelope.card["data"]["series_paise_per_qtl"] == [215000]

    p_with_db = await execute_agent_tool(
        "get_price_forecast",
        _ctx(user=farmer, db=object()),
        {"commodity": "onion", "mandi": "lasalgaon"},
    )
    assert len(p_with_db.envelope.card["data"]["series_paise_per_qtl"]) == 7
    assert p_with_db.envelope.card["data"]["series_paise_per_qtl"][-1] == 214000

    # 3. LOT_DRAFT normalizes None mandi -> "" for Krishi-Mitr ChatCards/ChatPanel.web
    l_res = await execute_agent_tool(
        "create_lot_draft",
        _ctx(user=farmer, db=None),
        {"commodity": "onion", "quantity": 1000, "unit": "kg"},
    )
    assert l_res.envelope.card["type"] == "LOT_DRAFT"
    assert l_res.envelope.card["data"]["mandi"] == ""
