import asyncio
import importlib.util
import os
import sys
from pathlib import Path

import pytest

from app.contracts import EvalRow, INTENT_LABELS
from app.nlp.hints import extract_hints

ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(ROOT))
from eval import eval_agent as ea  # noqa: E402

_spec = importlib.util.spec_from_file_location("gen_agent_eval", ROOT / "scripts/gen_agent_eval.py")
gen = importlib.util.module_from_spec(_spec)
_spec.loader.exec_module(gen)
ROWS = ea.load_rows(ROOT / "eval/data/agent_eval_60.jsonl", "all")


# ----------------------------------------------------------------------------- dataset
def test_committed_set_matches_generator():
    assert [r.model_dump() for r in gen.build()] == [r.model_dump() for r in ROWS]


def test_size_balance_and_all_ten_intents():
    assert len(ROWS) == 60 and len({r.id for r in ROWS}) == 60
    assert {r.expected_intent for r in ROWS} == set(INTENT_LABELS)
    for loc in ("mr", "hi", "en"):
        assert sum(r.locale == loc for r in ROWS) >= 15
    dev = {r.id for r in ROWS if r.split == "dev"}
    test = {r.id for r in ROWS if r.split == "test"}
    assert dev and test and not dev & test
    assert any(len(r.turns_original) > 1 for r in ROWS)  # multi-turn follow-ups exist
    assert sum(r.must_refuse for r in ROWS) >= 5
    assert {"khandi"} == {r.expected_args["unit_unknown"] for r in ROWS if "unit_unknown" in r.expected_args}


def test_expected_slots_agree_with_the_nlp_hint_layer_on_single_turn_rows():
    """If the hint extractor disagrees with the gold slots, the set (or the NLP layer) has a bug."""
    for r in ROWS:
        if len(r.turns_original) > 1:
            continue
        h = extract_hints(r.turns_original[-1])
        for k in ("commodity", "mandi", "quantity_kg", "unit_unknown"):
            if k in r.expected_args:
                assert h.get(k) == r.expected_args[k], (r.id, k)


# ----------------------------------------------------------------------------- metric math
def test_macro_f1_and_confusion():
    pairs = [("A", "A"), ("A", "B"), ("B", "B"), ("B", "B")]
    f1, per = ea.macro_f1(pairs)
    assert per["A"] == {"precision": 1.0, "recall": 0.5, "f1": pytest.approx(0.6667, abs=1e-3), "support": 2}
    assert per["B"]["recall"] == 1.0 and per["B"]["precision"] == pytest.approx(0.6667, abs=1e-3)
    assert f1 == pytest.approx((0.6667 + 0.8) / 2, abs=1e-3)
    assert ea.confusion(pairs) == {"A": {"A": 1, "B": 1}, "B": {"B": 2}}


def test_slot_f1_counts_wrong_missing_and_extra():
    items = [({"commodity": "cmd_onion", "quantity_kg": 1000}, {"commodity": "cmd_onion", "quantity_kg": 500}),
             ({"mandi": "mkt_pune"}, {}),
             ({}, {"grade": "A"})]
    r = ea.slot_f1(items)
    assert r["per_slot"]["commodity"]["tp"] == 1
    assert r["per_slot"]["quantity_kg"] == {"tp": 0, "fp": 1, "fn": 1, "f1": 0.0}
    assert r["per_slot"]["mandi"]["fn"] == 1 and r["per_slot"]["grade"]["fp"] == 1
    assert 0 < r["micro_f1"] < 1


def test_predicted_slots_reads_wrapper_output_and_ignores_errors():
    ok = {"error": None, "args": {"commodity": "onion", "mandi": "Lasalgaon", "quantity": 1000, "unit": "kg", "grade": "B"}}
    assert ea.predicted_slots(ok) == {"commodity": "cmd_onion", "mandi": "mkt_lasalgaon", "quantity_kg": 1000, "grade": "B"}
    assert ea.predicted_slots({"error": "NEEDS_INPUT", "args": {"commodity": "cmd_onion"}}) == {}
    assert "quantity_kg" not in ea.predicted_slots({"error": None, "args": {"quantity": 10, "unit": "bori"}})


def test_independent_number_check_flags_a_fabricated_number():
    env = {"ok": True, "data": {"expected_gain_paise": 185000}, "source": "x", "card": None, "error": None}
    good = {"reply": "Expected gain is Rs 1850.", "tool_envelopes": [{"tool": "compute_sale_window", "envelope": env}]}
    bad = {"reply": "Expected gain is Rs 9999.", "tool_envelopes": [{"tool": "compute_sale_window", "envelope": env}]}
    none = {"reply": "No numbers here.", "tool_envelopes": []}
    assert ea.numbers_grounded(good) is True and ea.numbers_grounded(bad) is False and ea.numbers_grounded(none) is None
    deva = {"reply": "अपेक्षित नफा रु. १८५० आहे.", "tool_envelopes": [{"tool": "compute_sale_window", "envelope": env}]}
    assert ea.numbers_grounded(deva) is True  # Devanagari digits are read, not skipped


def test_refusal_check_requires_the_template_and_no_tools_for_chemicals():
    from app.nlp.messages import get_message
    chem = next(r for r in ROWS if r.expected_intent == "OUT_OF_SCOPE" and r.must_refuse)
    assert ea.is_refusal_ok(chem, {"error_code": "CHEMICAL_ADVICE_REFUSED", "tools": [], "reply": "x", "lang": "en"})
    assert not ea.is_refusal_ok(chem, {"error_code": None, "tools": [], "reply": "x", "lang": "en"})
    win = next(r for r in ROWS if r.expected_intent == "WINDOW" and r.must_refuse)
    ok = {"error_code": "NO_ADVICE", "tools": [{}], "reply": get_message("NO_ADVICE", win.locale), "lang": win.locale}
    assert ea.is_refusal_ok(win, ok)
    assert not ea.is_refusal_ok(win, {**ok, "reply": "You should hold for 5 days."})


# ----------------------------------------------------------------------------- end to end (offline, frozen engine)
@pytest.mark.parametrize("pivot", ["on", "off"])
def test_harness_runs_the_real_engine_offline_for_both_pivots(pivot, monkeypatch):
    monkeypatch.setenv("TRANSLATE_PIVOT", "on")
    rows = [r for r in ROWS if r.split == "dev"]
    out = asyncio.run(ea.evaluate_once(rows, "baseline", "reference", pivot, False, "t"))
    m = out["metrics"]
    assert out["pivot"] == pivot and m["n"] == len(rows) and m["crashes"] == 0
    for key in ("intent_macro_f1", "tool_accuracy", "slot", "refusal_compliance", "number_check", "confusion", "turn_latency_ms"):
        assert key in m
    assert m["refusal_compliance"]["rate"] == 1.0  # the engine's refusal paths are deterministic code
    assert os.environ["TRANSLATE_PIVOT"] == "on"    # evaluate_once restores the caller's setting
    import app.engines.agent_engine as eng
    assert not isinstance(eng.execute_agent_tool, ea.Recorder)  # and un-patches the executor


def test_unknown_unit_never_becomes_a_quantity(monkeypatch):
    row = next(r for r in ROWS if "unit_unknown" in r.expected_args)
    out = asyncio.run(ea.evaluate_once([row], "baseline", "reference", "on", False, "u"))
    assert out["metrics"]["crashes"] == 0
    fails = {f["id"] for f in out["metrics"]["failures"]}
    assert row.id not in fails  # right tool, right intent; the NEEDS_INPUT path asked instead of guessing
