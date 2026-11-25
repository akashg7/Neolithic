import asyncio
import csv
import importlib.util
import json
import sys
from pathlib import Path

import pytest

from app.contracts import Translated

ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(ROOT))
from eval import eval_faithfulness as ef  # noqa: E402
from eval import eval_translation as et  # noqa: E402

_spec = importlib.util.spec_from_file_location("gen_translation_set", ROOT / "scripts/gen_translation_set.py")
gen = importlib.util.module_from_spec(_spec)
_spec.loader.exec_module(gen)
ROWS = et.load_rows(ROOT / "eval/data/translation_100.jsonl", "all")


# ----------------------------------------------------------------------------- translation set
def test_committed_set_matches_generator_and_is_100_balanced():
    assert [r.model_dump() for r in gen.build()] == [r.model_dump() for r in ROWS]
    assert len(ROWS) == 100 and sum(r.locale == "mr" for r in ROWS) == 50 and sum(r.locale == "hi" for r in ROWS) == 50
    dev = {r.id for r in ROWS if r.split == "dev"}
    test = {r.id for r in ROWS if r.split == "test"}
    assert dev and test and not dev & test


def _fakes(rows, drop_numbers=False):
    by_orig = {r.turns_original[0]: r for r in rows}

    async def to_en(text=None, audio=None, locale_hint=None):
        r = by_orig[text]
        english = r.turns_english[0]
        if drop_numbers:
            english = "".join(c for c in english if not c.isdigit())
        return Translated(original=text, english=english, source_lang=r.locale, hints={})

    async def back(texts, lang):
        return [("".join(c for c in t if not c.isdigit()) if drop_numbers else t) for t in texts], True
    return to_en, back


def test_evaluate_reports_full_preservation_for_a_faithful_translator():
    res = asyncio.run(et.evaluate(ROWS, *_fakes(ROWS)))
    assert res["n"] == 100 and not res["failures"]
    assert res["forward"]["numbers"]["rate"] == 1.0 and res["backward"]["numbers"]["rate"] == 1.0
    assert res["forward"]["quantity_kg"]["n"] > 30 and res["forward"]["quantity_kg"]["rate"] == 1.0


def test_evaluate_catches_a_translator_that_drops_numbers():
    res = asyncio.run(et.evaluate(ROWS, *_fakes(ROWS, drop_numbers=True)))
    # number-free rows pass vacuously, so the overall rate has a floor; quantity_kg is the sharp signal
    assert res["forward"]["numbers"]["rate"] < 0.6 and res["backward"]["numbers"]["rate"] < 0.6
    assert res["forward"]["quantity_kg"]["rate"] == 0.0
    assert res["failures"]


def test_evaluate_counts_a_crashing_translator_as_a_failure_not_a_crash():
    async def boom(**kw):
        raise RuntimeError("api down")
    res = asyncio.run(et.evaluate(ROWS[:5], boom, _fakes(ROWS)[1]))
    assert res["forward"]["numbers"]["rate"] == 0.0 and len(res["failures"]) >= 5


def test_rating_sheet_roundtrip_and_target(tmp_path):
    async def fake_from_en(texts, lang):
        return [f"[{lang}] {t}" for t in texts]
    p = tmp_path / "sheet.csv"
    assert asyncio.run(et.export_ratings(p, fake_from_en)) == 40
    assert et.summarise_ratings(p)["unrated"] == 40 and et.summarise_ratings(p)["target_met_ge_0_80"] is False
    with p.open(newline="", encoding="utf-8") as f:
        rows = list(csv.DictReader(f))
    for i, r in enumerate(rows):
        r["natural"] = "0" if i < 8 else "1"   # 32/40 = 80%
    with p.open("w", newline="", encoding="utf-8") as f:
        w = csv.DictWriter(f, fieldnames=list(rows[0]))
        w.writeheader()
        w.writerows(rows)
    s = et.summarise_ratings(p)
    assert s["all"]["natural_rate"] == 0.8 and s["target_met_ge_0_80"] is True
    assert s["mr"]["n"] == 20 and s["hi"]["n"] == 20


# ----------------------------------------------------------------------------- faithfulness judge
ENV = {"ok": True, "data": {"expected_gain_paise": 185000, "hold_days": 5}, "card": None}


def _rec(reply="Hold 5 days, gain Rs 1850.", **kw):
    base = {"id": "r1", "reply": reply, "error_code": None, "crash": None,
            "tool_envelopes": [{"tool": "compute_sale_window", "envelope": ENV}]}
    return {**base, **kw}


def test_parse_verdicts_handles_fences_and_rejects_garbage():
    raw = '```json\n{"claims":[{"claim":"a","verdict":"Supported"},{"claim":"b","verdict":"weird"}]}\n```'
    assert ef.parse_verdicts(raw) == [{"claim": "a", "verdict": "supported"}]
    with pytest.raises(ValueError):
        ef.parse_verdicts("no json here")


def test_judgeable_skips_templates_refusals_and_ungrounded_replies():
    from app.nlp.messages import get_message
    assert ef.is_judgeable(_rec())
    assert not ef.is_judgeable(_rec(reply=get_message("NO_ADVICE", "en"), error_code="NO_ADVICE"))
    assert not ef.is_judgeable(_rec(tool_envelopes=[]))
    assert not ef.is_judgeable(_rec(tool_envelopes=[{"tool": "t", "envelope": {"ok": False, "data": {}}}]))
    assert not ef.is_judgeable(_rec(crash="boom"))


def test_judge_records_scores_replies_and_claims():
    answers = iter([
        '{"claims":[{"claim":"hold 5 days","verdict":"supported"},{"claim":"gain Rs 1850","verdict":"supported"}]}',
        '{"claims":[{"claim":"hold 5 days","verdict":"supported"},{"claim":"gain Rs 9999","verdict":"contradicted"}]}',
        "not json at all",
    ])
    seen = []

    async def judge(system, user):
        seen.append((system, user))
        return next(answers)
    recs = [_rec(id="ok"), _rec(id="bad", reply="Hold 5 days, gain Rs 9999."), _rec(id="err"),
            _rec(id="skip", tool_envelopes=[])]
    out = asyncio.run(ef.judge_records(recs, judge))
    assert out["replies_judged"] == 2 and out["judge_errors"] == 1
    assert out["reply_faithful_rate"] == 0.5 and out["claim_supported_rate"] == pytest.approx(3 / 4)
    assert [u["id"] for u in out["unfaithful"]] == ["bad"]
    assert "185000" in seen[0][1] and "Rs 1850" in seen[0][1]       # judge sees sources and reply
    assert "never from your own knowledge" in seen[0][0]            # and is told to use sources only


def test_cli_refuses_same_provider_as_judge(monkeypatch):
    monkeypatch.setattr(sys, "argv", ["x", "--trace", "t.jsonl", "--agent-provider", "Groq", "--judge-provider", "groq"])
    with pytest.raises(SystemExit) as e:
        ef.main()
    assert "differ" in str(e.value)


# ----------------------------------------------------------------------------- bakeoff model resolver
_rs = importlib.util.spec_from_file_location("resolve_bakeoff_models", ROOT / "scripts/resolve_bakeoff_models.py")
rb = importlib.util.module_from_spec(_rs)
_rs.loader.exec_module(rb)


def test_resolver_picks_newest_matching_ids_and_skips_noise():
    groq = ["openai/gpt-oss-120b", "qwen/qwen3.6-27b", "qwen/qwen3.8-27b", "qwen/qwen3-32b", "whisper-large-v3"]
    assert rb.pick_model(groq, "groq-qwen-27b") == "qwen/qwen3.8-27b"
    gem = ["models/gemini-2.5-flash", "models/gemini-2.5-flash-lite", "models/gemini-3.5-flash",
           "models/gemini-3.5-flash-image", "models/gemini-3.5-pro"]
    assert rb.pick_model(gem, "gemini-flash") == "gemini-3.5-flash"
    assert rb.pick_model(["openai/gpt-oss-120b"], "groq-qwen-27b") is None


def test_resolver_only_touches_replace_placeholders(tmp_path, monkeypatch):
    p = tmp_path / "m.json"
    p.write_text(json.dumps({"candidates": [
        {"name": "groq-gpt-oss-120b", "base_url": "u", "api_key_env": "K", "model": "openai/gpt-oss-120b"},
        {"name": "gemini-flash", "base_url": "u", "api_key_env": "K", "model": "REPLACE_X"}]}))
    monkeypatch.setenv("K", "x")
    monkeypatch.setattr(rb, "list_models", lambda base, key: ["models/gemini-3.5-flash"])
    monkeypatch.setattr(sys, "argv", ["x", "--write", "--path", str(p)])
    assert rb.main() == 0
    out = json.loads(p.read_text())["candidates"]
    assert out[0]["model"] == "openai/gpt-oss-120b" and out[1]["model"] == "gemini-3.5-flash"


def test_rerank_decision_rule():
    _s = importlib.util.spec_from_file_location("bench_rerank", ROOT / "scripts/bench_rerank.py")
    br = importlib.util.module_from_spec(_s)
    _s.loader.exec_module(br)
    assert br.decide(120, 250) == "KEEP" and br.decide(120, 301) == "DROP" and br.decide(400, 10) == "DROP"
    assert br.pct([1, 2, 3, 4, 100], 0.95) == 100
