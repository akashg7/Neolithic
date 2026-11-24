"""Tests for all 4 safety guards and the full `AgentEngine.run_turn` loop."""
from __future__ import annotations

import json
from typing import Any

import pytest

from app.agents.guards import (
    check_language_compliance,
    check_no_advice_compliance,
    check_numbers_against_tools,
    is_chemical_query_or_advice,
)
from app.agents.llm_client import ILLMClient, LLMResponse, LLMToolCall, LLMUnavailableError
from app.agents.memory import SessionMemoryStore
from app.agents.tool_bridge import ExecutedToolCall
from app.agents.tools import decision as decision_mod
from app.contracts import Intent, ToolResult, Translated
from app.engines.agent_engine import AgentEngine
from app.nlp import translate as translate_mod
from app.nlp.messages import MESSAGES
from app.schemas.agent import ScreenContext


class ScriptedLLM(ILLMClient):
    """Scripted multi-step LLM responses for deterministic loop tests."""

    def __init__(self, script: list[LLMResponse]):
        self.script = list(script)
        self.calls: list[list[dict[str, Any]]] = []

    async def complete(self, messages, tools=None, *, temperature=0.2, tool_choice="auto", max_tokens=None):
        self.calls.append(messages)
        if not self.script:
            raise AssertionError("ScriptedLLM ran out of scripted responses")
        return self.script.pop(0)


def _tc(name: str, args: dict, cid: str = "c1") -> LLMToolCall:
    return LLMToolCall(id=cid, name=name, arguments=args, raw_arguments=json.dumps(args))


def _window_result(action: str = "HOLD") -> dict:
    return {
        "action": action,
        "recommendation": action,
        "confidence": "MEDIUM" if action != "NO_ADVICE" else "LOW",
        "hold_days": 5 if action == "HOLD" else None,
        "band_width_bps": 2100 if action != "NO_ADVICE" else 4200,
        "expected_gain_paise": 185000 if action == "HOLD" else 0,
        "worst_case_paise": 40000 if action == "HOLD" else 0,
        "sell_now_net_paise_per_qtl": 205000,
        "itemised_costs": {"total_paise_per_qtl": 9000},
        "pledge_quote": None,
        "refusal_reason": "BAND_TOO_WIDE" if action == "NO_ADVICE" else None,
        "explain_mr": "थांबा",
        "explain_en": "Hold",
        "data_source": "AGMARKNET_ML",
        "inputs": {
            "commodity": {"slug": "cmd_onion", "name": "Onion", "name_mr": "कांदा", "id": 1},
            "market": {"slug": "mkt_lasalgaon", "name": "Lasalgaon APMC", "name_mr": "लासलगाव", "id": 1},
            "quantity_kg": 1000,
            "transport_included": True,
            "spot_price_source": "AGMARKNET",
            "spot_price_date": "2026-11-24",
        },
    }


def test_unit_guards_directly():
    tool_call = ExecutedToolCall(
        tool_name="compute_sale_window",
        envelope=ToolResult(
            ok=True,
            source="window_engine_v1",
            data={"action": "HOLD", "hold_days": 5, "expected_gain_paise": 185000, "worst_case_paise": 40000},
            card={"type": "WINDOW_VERDICT", "data": {"quantity_kg": 1000}},
        ),
    )

    # Paise->rupees (1850, 400), kg->quintals (10), kg->bori (20), 1-in-10 allowed
    assert check_numbers_against_tools(
        "Hold 10 quintals (20 bori) for 5 days; expected gain is Rs 1850 and worst 1-in-10 case is Rs 400.",
        [tool_call],
    ) is None

    # Fabricated number rejected
    bad = check_numbers_against_tools("Expected gain is Rs 9999 in 5 days.", [tool_call])
    assert bad is not None and bad.guard == "number_check"

    # Language guard
    assert check_language_compliance("कांदा भाव २१५०", pivot_on=True, target_lang="mr").guard == "language"
    assert check_language_compliance("Modal price is Rs 2150.", pivot_on=True, target_lang="mr") is None
    assert check_language_compliance("Price is Rs 2150", pivot_on=False, target_lang="mr").guard == "language"
    assert check_language_compliance("कांदा भाव २१५० रुपये आहे", pivot_on=False, target_lang="mr") is None

    # Chemicals guard
    assert is_chemical_query_or_advice("कांद्यावरील करपा रोगासाठी कोणत्या कीटकनाशकाची किती फवारणी करू?")
    assert is_chemical_query_or_advice("Which pesticide and how much should I spray?")
    assert not is_chemical_query_or_advice("How do I store onions to prevent sprouting?")


@pytest.mark.asyncio
async def test_chemical_query_refused_without_llm_call(fake_redis):
    llm = ScriptedLLM([])  # will assert if called
    engine = AgentEngine(llm_client=llm, memory=SessionMemoryStore(fake_redis))
    resp = await engine.run_turn(
        db=None,
        user=None,
        session_id="s_chem",
        locale="mr",
        text="कांद्यावरील करपा रोगासाठी कोणत्या कीटकनाशकाची किती फवारणी करू?",
        persist_log=False,
    )
    assert resp.intent_detected == Intent.OUT_OF_SCOPE
    assert resp.error_code == "CHEMICAL_ADVICE_REFUSED"
    assert "KVK" in resp.reply_text
    assert len(llm.calls) == 0


@pytest.mark.asyncio
async def test_engine_full_loop_builds_cards_and_saves_english_memory(monkeypatch, farmer, fake_redis):
    async def fake_sw(db, **kw):
        return _window_result("HOLD")

    monkeypatch.setattr(decision_mod, "sale_window", fake_sw)
    monkeypatch.setenv("TRANSLATE_BACKEND", "stub")
    monkeypatch.setenv("TRANSLATE_PIVOT", "on")

    llm = ScriptedLLM(
        [
            LLMResponse(
                content=None,
                tool_calls=[
                    _tc("compute_sale_window", {"commodity": "onion", "mandi": "lasalgaon", "quantity": 20, "unit": "bori"})
                ],
            ),
            LLMResponse(
                content=None,
                tool_calls=[
                    _tc(
                        "final_answer",
                        {
                            "reply_text": "Hold your 1000 kg onion for 5 days; expected gain is Rs 1850 and worst 1-in-10 case is Rs 400.",
                            "intent": "WINDOW",
                            "quick_replies": ["Create lot", "Check storage cost"],
                        },
                    )
                ],
            ),
        ]
    )
    mem = SessionMemoryStore(fake_redis)
    engine = AgentEngine(llm_client=llm, memory=mem)
    resp = await engine.run_turn(
        db=None,
        user=farmer,
        session_id="s_hold",
        locale="mr",
        screen_context=ScreenContext(current_screen="S4_Home"),
        text="माझ्याकडे २० बोरी कांदा आहे, लासलगावला कधी विकू?",
        persist_log=False,
    )

    assert resp.intent_detected == Intent.WINDOW
    assert resp.error_code is None
    assert len(resp.cards) == 1 and resp.cards[0].type == "WINDOW_VERDICT"
    assert resp.ui_action is not None and resp.ui_action.target_screen == "S9_Verdict"
    assert resp.citations and resp.citations[0].source == "window_engine_v1"
    assert resp.reply_text.startswith("[mr] Hold your 1000 kg onion")
    assert len(resp.quick_replies) == 2

    # Memory stores compact English summary
    turns = await mem.load_turns("s_hold")
    assert len(turns) == 1
    assert "Hold your 1000 kg onion" in turns[0].assistant
    assert "compute_sale_window: action=HOLD" in turns[0].tool_summaries[0]


@pytest.mark.asyncio
async def test_number_guard_retries_once_then_falls_back_to_card_data(monkeypatch, farmer, fake_redis):
    async def fake_sw(db, **kw):
        return _window_result("HOLD")

    monkeypatch.setattr(decision_mod, "sale_window", fake_sw)
    monkeypatch.setenv("TRANSLATE_BACKEND", "stub")
    monkeypatch.setenv("TRANSLATE_PIVOT", "on")

    # 1st final_answer hallucinates Rs 9999 -> retried -> 2nd hallucinates Rs 8888 -> pre-translated fallback
    llm = ScriptedLLM(
        [
            LLMResponse(content=None, tool_calls=[_tc("compute_sale_window", {"commodity": "onion", "mandi": "lasalgaon", "quantity": 20, "unit": "bori"})]),
            LLMResponse(content=None, tool_calls=[_tc("final_answer", {"reply_text": "Expected gain is Rs 9999.", "intent": "WINDOW"})]),
            LLMResponse(content=None, tool_calls=[_tc("final_answer", {"reply_text": "Expected gain is Rs 8888.", "intent": "WINDOW"})]),
        ]
    )
    engine = AgentEngine(llm_client=llm, memory=SessionMemoryStore(fake_redis))
    resp = await engine.run_turn(
        db=None,
        user=farmer,
        session_id="s_num_fail",
        locale="mr",
        text="माझ्याकडे २० बोरी कांदा आहे, लासलगावला कधी विकू?",
        persist_log=False,
    )
    assert len(llm.calls) == 3
    assert resp.error_code == "NUMBER_CHECK_FAILED"
    assert MESSAGES["FALLBACK"]["mr"] in resp.reply_text
    assert resp.cards and resp.cards[0].type == "WINDOW_VERDICT"


@pytest.mark.asyncio
async def test_post_translation_number_mismatch_uses_card_fallback(monkeypatch, farmer, fake_redis):
    async def fake_sw(db, **kw):
        return _window_result("HOLD")

    monkeypatch.setattr(decision_mod, "sale_window", fake_sw)
    monkeypatch.setenv("TRANSLATE_PIVOT", "on")

    async def fake_to_en(*a, **k):
        return Translated(
            original="२० बोरी कांदा लासलगावला कधी विकू?",
            english="I have 20 bags of onion at Lasalgaon, when should I sell?",
            source_lang="mr",
            hints={"commodity": "cmd_onion", "mandi": "mkt_lasalgaon", "quantity_kg": 1000},
        )

    async def broken_back_translate(texts, lang):
        return ["[broken translation without numbers]"], False

    from app.engines import agent_engine as engine_mod

    monkeypatch.setattr(engine_mod, "to_english", fake_to_en)
    monkeypatch.setattr(engine_mod, "translate_back_checked", broken_back_translate)

    llm = ScriptedLLM(
        [
            LLMResponse(content=None, tool_calls=[_tc("compute_sale_window", {"commodity": "onion", "mandi": "lasalgaon", "quantity": 20, "unit": "bori"})]),
            LLMResponse(content=None, tool_calls=[_tc("final_answer", {"reply_text": "Hold for 5 days; gain Rs 1850.", "intent": "WINDOW"})]),
        ]
    )
    engine = AgentEngine(llm_client=llm, memory=SessionMemoryStore(fake_redis))
    resp = await engine.run_turn(
        db=None,
        user=farmer,
        session_id="s_back_fail",
        locale="mr",
        text="२० बोरी कांदा लासलगावला कधी विकू?",
        persist_log=False,
    )
    assert resp.error_code == "TRANSLATION_NUMBER_MISMATCH"
    assert MESSAGES["FALLBACK"]["mr"] in resp.reply_text


@pytest.mark.asyncio
async def test_no_advice_guard_overrides_model_hold_recommendation(monkeypatch, farmer, fake_redis):
    async def fake_sw(db, **kw):
        return _window_result("NO_ADVICE")

    monkeypatch.setattr(decision_mod, "sale_window", fake_sw)
    monkeypatch.setenv("TRANSLATE_BACKEND", "stub")
    monkeypatch.setenv("TRANSLATE_PIVOT", "on")

    llm = ScriptedLLM(
        [
            LLMResponse(content=None, tool_calls=[_tc("compute_sale_window", {"commodity": "onion", "mandi": "lasalgaon", "quantity": 20, "unit": "bori"})]),
            LLMResponse(content=None, tool_calls=[_tc("final_answer", {"reply_text": "You should hold for 7 days.", "intent": "WINDOW"})]),
        ]
    )
    engine = AgentEngine(llm_client=llm, memory=SessionMemoryStore(fake_redis))
    resp = await engine.run_turn(
        db=None,
        user=farmer,
        session_id="s_noadvice",
        locale="mr",
        text="माझ्याकडे २० बोरी कांदा आहे, लासलगावला कधी विकू?",
        persist_log=False,
    )
    assert resp.error_code == "NO_ADVICE"
    assert resp.reply_text == MESSAGES["NO_ADVICE"]["mr"]
    na_exec = ExecutedToolCall(
        tool_name="compute_sale_window",
        envelope=ToolResult(ok=True, source="window_engine_v1", data={"action": "NO_ADVICE"}),
    )
    assert check_no_advice_compliance("You should hold for 7 days.", [na_exec]).guard == "NO_ADVICE"
    assert check_no_advice_compliance("We cannot advise holding or selling right now.", [na_exec]) is None


@pytest.mark.asyncio
async def test_language_guard_retries_devanagari_when_pivot_on(monkeypatch, fake_redis):
    monkeypatch.setenv("TRANSLATE_BACKEND", "stub")
    monkeypatch.setenv("TRANSLATE_PIVOT", "on")

    llm = ScriptedLLM(
        [
            LLMResponse(content=None, tool_calls=[_tc("final_answer", {"reply_text": "नमस्कार!", "intent": "SMALLTALK"})]),
            LLMResponse(content=None, tool_calls=[_tc("final_answer", {"reply_text": "Hello! How can I help you today?", "intent": "SMALLTALK"})]),
        ]
    )
    engine = AgentEngine(llm_client=llm, memory=SessionMemoryStore(fake_redis))
    resp = await engine.run_turn(
        db=None,
        user=None,
        session_id="s_lang",
        locale="mr",
        text="नमस्कार",
        persist_log=False,
    )
    assert len(llm.calls) == 2
    assert resp.intent_detected == Intent.SMALLTALK
    assert resp.reply_text == "[mr] Hello! How can I help you today?"


@pytest.mark.asyncio
async def test_parallel_tool_calls_from_model_preserve_protocol_and_execute_first_only(monkeypatch, farmer, fake_redis):
    async def fake_sw(db, **kw):
        return _window_result("HOLD")

    monkeypatch.setattr(decision_mod, "sale_window", fake_sw)
    monkeypatch.setenv("TRANSLATE_BACKEND", "stub")
    monkeypatch.setenv("TRANSLATE_PIVOT", "on")

    llm = ScriptedLLM(
        [
            LLMResponse(
                content=None,
                tool_calls=[
                    _tc("compute_sale_window", {"commodity": "onion", "mandi": "lasalgaon", "quantity": 20, "unit": "bori"}, cid="c1"),
                    _tc("get_farmer_portfolio", {}, cid="c2"),
                ],
            ),
            LLMResponse(
                content=None,
                tool_calls=[_tc("final_answer", {"reply_text": "Hold for 5 days; gain Rs 1850.", "intent": "WINDOW"})],
            ),
        ]
    )
    engine = AgentEngine(llm_client=llm, memory=SessionMemoryStore(fake_redis))
    resp = await engine.run_turn(
        db=None,
        user=farmer,
        session_id="s_par",
        locale="en",
        text="I have 20 bags of onion at Lasalgaon, should I sell?",
        persist_log=False,
    )
    assert resp.intent_detected == Intent.WINDOW
    # Second LLM call receives tool messages for BOTH c1 and c2
    tool_msgs = [m for m in llm.calls[1] if m["role"] == "tool"]
    assert [m["tool_call_id"] for m in tool_msgs] == ["c1", "c2"]
    assert "Only one tool call per step" in tool_msgs[1]["content"]


@pytest.mark.asyncio
async def test_llm_unavailable_degrades_gracefully(monkeypatch, fake_redis):
    class DownLLM(ILLMClient):
        async def complete(self, *a, **k):
            raise LLMUnavailableError("down")

    monkeypatch.setenv("TRANSLATE_BACKEND", "stub")
    engine = AgentEngine(llm_client=DownLLM(), memory=SessionMemoryStore(fake_redis))
    resp = await engine.run_turn(
        db=None,
        user=None,
        session_id="s_down",
        locale="mr",
        text="भाव काय?",
        persist_log=False,
    )
    assert resp.error_code == "LLM_UNAVAILABLE"
    assert resp.reply_text == MESSAGES["FALLBACK"]["mr"]


@pytest.mark.asyncio
async def test_translate_pivot_off_skips_translation_and_enforces_devanagari(monkeypatch, fake_redis):
    monkeypatch.setenv("TRANSLATE_BACKEND", "stub")
    monkeypatch.setenv("TRANSLATE_PIVOT", "off")

    llm = ScriptedLLM(
        [
            # First call replies in English -> language guard retries when pivot=off for mr
            LLMResponse(content=None, tool_calls=[_tc("final_answer", {"reply_text": "Hello farmer, how can I help?", "intent": "SMALLTALK"})]),
            LLMResponse(content=None, tool_calls=[_tc("final_answer", {"reply_text": "नमस्कार, मी तुम्हाला कशी मदत करू शकतो?", "intent": "SMALLTALK"})]),
        ]
    )
    engine = AgentEngine(llm_client=llm, memory=SessionMemoryStore(fake_redis))
    resp = await engine.run_turn(
        db=None,
        user=None,
        session_id="s_nopivot",
        locale="mr",
        text="नमस्कार",
        persist_log=False,
    )
    assert len(llm.calls) == 2
    assert resp.reply_text == "नमस्कार, मी तुम्हाला कशी मदत करू शकतो?"
