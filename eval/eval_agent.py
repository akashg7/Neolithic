"""End-to-end agent evaluation on the frozen `AgentEngine`.

    # real numbers: live LLM chain from .env (Groq/Gemini/...), real Sarvam translation, real Qdrant:
    python eval/eval_agent.py --split test --llm live --translate live --rag real --pivot both --out eval/results/agent_test.json
    # isolate the agent from machine translation (uses the reference English in the dataset):
    python eval/eval_agent.py --split test --llm live --translate reference --pivot both
    # offline plumbing check with a scripted keyword router (NOT a language model, and its keywords were
    # written while looking at this dataset, so its scores are NOT a baseline for any real model):
    python eval/eval_agent.py --split dev --llm baseline --translate reference --pivot both

What runs for real: `AgentEngine.run_turn` (prompt, loop, guards, translation hooks, response builder).
What is a fixture: the DOMAIN tools that need Postgres/forecast models (sale window, price, grade, lot
draft, portfolio) return recorded, deterministic results, so runs are repeatable and numbers are
known. The window fixture returns NO_ADVICE for WINDOW rows marked must_refuse and HOLD otherwise.
Navigation, onboarding extraction and (with --rag real) knowledge search execute for real.

Metrics (scored turn = last turn of each conversation):
  intent macro-F1       response.intent_detected vs expected_intent, macro over labels in the gold set
  tool accuracy         first executed tool (or final_answer when none) vs expected_tool
  slot F1 (micro)       commodity, mandi, quantity_kg, grade read from the tool arguments after the
                        wrapper (hint-wins, unit conversion); unknown units must yield NO quantity_kg
  refusal compliance    must_refuse rows: CHEMICAL_ADVICE_REFUSED for chemical asks, NO_ADVICE with the
                        pre-translated template and no hold/sell directive for window asks
  number check          engine-level: no NUMBER_CHECK_FAILED / TRANSLATION_NUMBER_MISMATCH error code;
                        independent: every number in the FINAL localized reply is grounded in a tool result
Report the TEST split in final numbers; tune on dev. Run once per pivot setting.
"""
from __future__ import annotations

import argparse
import asyncio
import json
import os
import statistics
import sys
import time
from collections import Counter, defaultdict
from pathlib import Path
from types import SimpleNamespace
from typing import Any, Optional

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))
from app.contracts import EvalRow, Intent, ToolResult, Translated  # noqa: E402
from app.nlp.hints import extract_hints  # noqa: E402
from app.nlp.lexicon import resolve_commodity, resolve_mandi  # noqa: E402

DEFAULT_SET = ROOT / "eval/data/agent_eval_60.jsonl"
SLOTS = ("commodity", "mandi", "quantity_kg", "grade")
NUMBER_ERRORS = {"NUMBER_CHECK_FAILED", "TRANSLATION_NUMBER_MISMATCH"}


# ----------------------------------------------------------------------------- fixtures
class FakeRedis:
    """Minimal async get/set/delete so SessionMemoryStore works without a Redis server."""

    def __init__(self) -> None:
        self.store: dict[str, str] = {}

    async def get(self, key):
        return self.store.get(key)

    async def set(self, key, value, ex=None):
        self.store[key] = value
        return True

    async def delete(self, key):
        return 1 if self.store.pop(key, None) is not None else 0


def window_fixture(commodity: str, mandi: str, qty_kg: int, no_advice: bool) -> dict:
    if no_advice:
        data = {"action": "NO_ADVICE", "recommendation": "NO_ADVICE", "confidence": "LOW", "hold_days": None,
                "band_width_bps": 4200, "expected_gain_paise": 0, "worst_case_paise": 0,
                "refusal_reason": "BAND_TOO_WIDE", "data_source": "AGMARKNET_ML"}
    else:
        data = {"action": "HOLD", "recommendation": "HOLD", "confidence": "MEDIUM", "hold_days": 5,
                "band_width_bps": 2100, "expected_gain_paise": 185000, "worst_case_paise": 40000,
                "sell_now_net_paise_per_qtl": 205000, "refusal_reason": None, "data_source": "AGMARKNET_ML"}
    data["inputs"] = {"commodity": {"slug": commodity}, "market": {"slug": mandi}, "quantity_kg": qty_kg}
    return data


def fixture_result(name: str, args: dict, no_advice: bool) -> Optional[ToolResult]:
    if name == "compute_sale_window":
        qty = int(args.get("quantity") or 1000)
        data = window_fixture(str(args.get("commodity")), str(args.get("mandi")), qty, no_advice)
        return ToolResult(ok=True, data=data, source="window_engine_v1",
                          card={"type": "WINDOW_VERDICT", "data": {"action": data["action"], "quantity_kg": qty}})
    if name == "get_price_forecast":
        data = {"snapshot": {"modal_paise_per_qtl": 215000, "min_paise_per_qtl": 190000, "max_paise_per_qtl": 230000,
                             "change_bps": 250},
                "forecast": {"summary": "p50 220000 paise per quintal in 7 days", "points": []}}
        return ToolResult(ok=True, data=data, source="price_engine_v1",
                          card={"type": "PRICE_SNAPSHOT", "data": {"modal_price_paise_per_qtl": 215000}})
    if name == "calculate_grade":
        return ToolResult(ok=True, data={"grade": "B", "tip": "Dry the produce for one more day"},
                          source="grading_engine", card=None)
    if name == "create_lot_draft":
        qty = int(args.get("quantity") or 0)
        return ToolResult(ok=True, data={"quantity_kg": qty, "status": "draft"}, source="lot_service",
                          card={"type": "LOT_DRAFT", "data": {"quantity_kg": qty}})
    if name == "get_farmer_portfolio":
        return ToolResult(ok=True, data={"active_lots": 2, "open_offers": 1, "escrow_deals": 0},
                          source="portfolio_service", card=None)
    return None


class Recorder:
    """Patched in place of `execute_agent_tool`; records what the model asked for after the wrapper."""

    def __init__(self, real_rag: bool) -> None:
        self.real_rag = real_rag
        self.calls: list[dict] = []
        self.no_advice = False
        self.real = None  # set by install()

    async def __call__(self, name, ctx, args, *, hints=None):
        from app.agents import tool_bridge as tb
        raw, hints = dict(args or {}), dict(hints or {})
        needs_q = name in ("compute_sale_window", "create_lot_draft")
        merged, err = tb._apply_hint_wins_and_units(name, raw, hints, needs_quantity=needs_q)
        entry = {"tool": name, "args": merged, "error": err.error if err else None}
        self.calls.append(entry)
        if err is not None:
            entry["envelope"] = err.model_dump()
            return tb.ExecutedToolCall(name, err, summary=err.error or "")
        fx = fixture_result(name, merged, self.no_advice)
        if fx is not None and not (name == "search_agri_knowledge" and self.real_rag):
            entry["envelope"] = fx.model_dump()
            return tb.ExecutedToolCall(name, fx, summary=f"[{name}: ok]")
        out = await self.real(name, ctx, args, hints=hints)
        entry["envelope"] = out.envelope.model_dump()
        return out


def install_recorder(real_rag: bool) -> Recorder:
    import app.engines.agent_engine as eng
    rec = Recorder(real_rag)
    rec.real = eng.execute_agent_tool
    eng.execute_agent_tool = rec
    return rec


# ----------------------------------------------------------------------------- rule-based baseline "LLM"
class RuleBasedLLM:
    """A scripted keyword router, NOT a language model. Its keywords were written against this dataset's
    phrasings, so it scores high by construction: it only proves the harness, engine, guards and
    metrics are wired together offline. Never quote its numbers as a baseline."""

    def __init__(self) -> None:
        from app.agents.llm_client import LLMResponse, LLMToolCall
        self._R, self._C = LLMResponse, LLMToolCall

    @staticmethod
    def _tool_for(text: str, screen_onboarding: bool) -> tuple[str, dict, str]:
        t = text.lower()
        hints_blob = t
        has = lambda *ws: any(w in hints_blob for w in ws)  # noqa: E731
        if screen_onboarding:
            return "extract_onboarding_profile", {}, "ONBOARD"
        if has("scheme", "kisan credit", "kcc", "pm-kisan", "insurance", "loan", "wdra", "moisture is allowed", "how many kilograms",
               "counter an offer", "size classes", "receive the buyer", "interest"):
            return "search_agri_knowledge", {"query": text}, "RAG"
        if has("open the", "take me to", "show the prices page", "screen"):
            return "navigate_screen", {"target_screen": "home"}, "NAVIGATE"
        if has("my active lots", "my offers", "offers do i", "status of my", "offers have i"):
            return "get_farmer_portfolio", {}, "PORTFOLIO"
        if has("grade"):
            return "calculate_grade", {}, "GRADE"
        if has("list a lot", "create a lot", "list ", "put ", "lot"):
            return "create_lot_draft", {}, "LOT"
        if has("sell", "hold", "wait"):
            return "compute_sale_window", {}, "WINDOW"
        if has("price", "rate", "forecast"):
            return "get_price_forecast", {}, "PRICE"
        if has("hello", "thank"):
            return "final_answer", {"reply_text": "You are welcome.", "intent": "SMALLTALK"}, "SMALLTALK"
        return "final_answer", {"reply_text": "I can only help with farming and this app.", "intent": "OUT_OF_SCOPE"}, "OUT_OF_SCOPE"

    async def complete(self, messages, tools=None, *, temperature=0.2, tool_choice="auto", max_tokens=None):
        last_user = next(m for m in reversed(messages) if m["role"] == "user")["content"]
        body = last_user.split("\n")
        text = " ".join(body[1:-1]) if len(body) >= 3 else last_user
        ctx_line = body[0] if body else ""
        used = [m for m in messages if m["role"] == "tool"]
        deva = any("ऀ" <= c <= "ॿ" for c in text)
        # Pivot-off mode feeds the farmer's own words: translate common cues to English keywords.
        if deva:
            for src, dst in (("विकू", "sell"), ("थांबू", "wait"), ("बेचूं", "sell"), ("रुकूं", "wait"), ("बेचना", "sell"),
                             ("बेच", "sell"), ("रोक", "hold"), ("भाव", "price"), ("दर", "price"), ("रेट", "price"),
                             ("अंदाज", "forecast"), ("लॉट", "lot"), ("ग्रेड", "grade"), ("क्वालिटी", "grade"),
                             ("ऑफर", "offers"), ("डील", "offers"), ("स्थिती", "status of my"), ("स्थिति", "status of my"),
                             ("व्याज", "interest"), ("लोन", "loan"), ("किस्त", "pm-kisan"), ("ओलावा", "moisture is allowed"),
                             ("बोरीत", "how many kilograms"), ("खरीदार", "receive the buyer"), ("उघडा", "open the"),
                             ("खोलो", "open the"), ("दिखाओ", "show the prices page"), ("सक्रिय", "my active lots")):
                text = text.replace(src, f" {dst} ")
        if used:
            _, _, intent = self._tool_for(text, "S3_Profile" in ctx_line)
            ok_text = "Here is the result."
            if deva and os.environ.get("TRANSLATE_PIVOT") == "off":
                ok_text = "तुमची विनंती पूर्ण झाली आहे."
            return self._R(content=None, tool_calls=[self._C(id="f", name="final_answer", arguments={
                "reply_text": ok_text, "intent": intent}, raw_arguments=json.dumps({"reply_text": ok_text, "intent": intent}))],
                model="baseline", provider="baseline", latency_ms=0.0)
        tool, args, intent = self._tool_for(text, "S3_Profile" in ctx_line)
        if tool == "final_answer" and os.environ.get("TRANSLATE_PIVOT") == "off" and deva:
            args = {**args, "reply_text": "मी फक्त शेती आणि या ॲपबद्दल मदत करू शकतो."}
        return self._R(content=None, tool_calls=[self._C(id="c1", name=tool, arguments=args, raw_arguments=json.dumps(args))],
                       model="baseline", provider="baseline", latency_ms=0.0)


# ----------------------------------------------------------------------------- metrics
def macro_f1(pairs: list[tuple[str, str]]) -> tuple[float, dict]:
    labels = sorted({g for g, _ in pairs})
    per = {}
    for lab in labels:
        tp = sum(1 for g, p in pairs if g == lab and p == lab)
        fp = sum(1 for g, p in pairs if g != lab and p == lab)
        fn = sum(1 for g, p in pairs if g == lab and p != lab)
        prec = tp / (tp + fp) if tp + fp else 0.0
        rec = tp / (tp + fn) if tp + fn else 0.0
        per[lab] = {"precision": round(prec, 4), "recall": round(rec, 4),
                    "f1": round(2 * prec * rec / (prec + rec), 4) if prec + rec else 0.0, "support": tp + fn}
    mean = sum(v["f1"] for v in per.values()) / len(per) if per else 0.0
    return round(mean, 4), per


def confusion(pairs: list[tuple[str, str]]) -> dict:
    out: dict[str, Counter] = defaultdict(Counter)
    for g, p in pairs:
        out[g][p] += 1
    return {g: dict(c) for g, c in sorted(out.items())}


def predicted_slots(call: Optional[dict]) -> dict:
    """Slots as the tool actually received them, after the wrapper."""
    if not call or call["error"]:
        return {}
    a, out = call["args"], {}
    if a.get("commodity"):
        v = str(a["commodity"])
        out["commodity"] = resolve_commodity(v) or v
    if a.get("mandi"):
        v = str(a["mandi"])
        out["mandi"] = resolve_mandi(v) or v
    if a.get("quantity") is not None and str(a.get("unit") or "kg") == "kg":
        try:
            out["quantity_kg"] = int(float(a["quantity"]))
        except (TypeError, ValueError):
            pass
    if a.get("grade"):
        out["grade"] = a["grade"]
    return out


def slot_f1(items: list[tuple[dict, dict]]) -> dict:
    tp, fp, fn = Counter(), Counter(), Counter()
    for exp, got in items:
        for s in SLOTS:
            e, g = exp.get(s), got.get(s)
            if e is not None and g == e:
                tp[s] += 1
            else:
                if g is not None:
                    fp[s] += 1
                if e is not None:
                    fn[s] += 1
    def f1(t, p, n):
        pr = t / (t + p) if t + p else 0.0
        rc = t / (t + n) if t + n else 0.0
        return round(2 * pr * rc / (pr + rc), 4) if pr + rc else 0.0
    per = {s: {"tp": tp[s], "fp": fp[s], "fn": fn[s], "f1": f1(tp[s], fp[s], fn[s])} for s in SLOTS}
    T, Fp, Fn = sum(tp.values()), sum(fp.values()), sum(fn.values())
    return {"micro_f1": f1(T, Fp, Fn), "per_slot": per}


def is_refusal_ok(row: EvalRow, rec: dict) -> bool:
    from app.nlp.messages import get_message
    if row.expected_intent == "OUT_OF_SCOPE":  # chemical ask
        return rec["error_code"] == "CHEMICAL_ADVICE_REFUSED" and not rec["tools"]
    if row.expected_intent == "WINDOW":
        return (rec["error_code"] == "NO_ADVICE" and rec["reply"] == get_message("NO_ADVICE", rec["lang"])
                and "HOLD" not in rec["reply"].upper().split())
    return False


def numbers_grounded(rec: dict) -> Optional[bool]:
    """Independent post-translation check on the final localized reply; None when it has no numbers."""
    from app.agents.guards import check_numbers_against_tools
    from app.agents.tool_bridge import ExecutedToolCall
    from app.nlp.numbers import extract_numbers
    if not extract_numbers(rec["reply"]):
        return None
    executed = [ExecutedToolCall(tool_name=t["tool"], envelope=ToolResult(**t["envelope"])) for t in rec["tool_envelopes"]]
    return check_numbers_against_tools(rec["reply"], executed) is None


# ----------------------------------------------------------------------------- run
async def run_conversation(engine, rec: Recorder, row: EvalRow, *, translate: str, tag: str) -> dict:
    session = f"eval_{tag}_{row.id}"
    last: dict = {}
    for i, (orig, eng_text) in enumerate(zip(row.turns_original, row.turns_english)):
        rec.calls.clear()
        rec.no_advice = bool(row.must_refuse and row.expected_intent == "WINDOW")
        pre = None
        if translate == "reference":
            pre = Translated(original=orig, english=eng_text, source_lang=row.locale, hints=extract_hints(orig))
        t0 = time.perf_counter()
        try:
            resp = await engine.run_turn(db=None, user=None, session_id=session, locale=row.locale,
                                         screen_context=_screen(row), text=orig, pre_translated=pre, persist_log=False)
            err = None
        except Exception as e:  # a crash is a failed turn, not a crashed eval
            resp, err = None, f"{type(e).__name__}: {str(e)[:160]}"
        ms = (time.perf_counter() - t0) * 1000
        last = {"id": row.id, "turn_index": i, "ms": round(ms, 1), "crash": err, "original": orig, "locale": row.locale,
                "tools": [{k: v for k, v in c.items() if k != "envelope"} for c in rec.calls],
                "tool_envelopes": [{"tool": c["tool"], "envelope": c["envelope"]} for c in rec.calls if "envelope" in c]}
        if resp is not None:
            last.update(intent=resp.intent_detected.value, reply=resp.reply_text, error_code=resp.error_code,
                        card_types=[c.type for c in resp.cards], lang=row.locale)
    return last


def _screen(row: EvalRow):
    from app.schemas.agent import ScreenContext
    keys = ("current_screen", "active_commodity_id", "active_market_id", "active_lot_id")
    return ScreenContext(**{k: v for k, v in (row.screen_context or {}).items() if k in keys})


def score(rows: list[EvalRow], recs: list[dict]) -> dict:
    by_id = {r["id"]: r for r in recs}
    intent_pairs, tool_ok, slot_items, ref_ok, ref_n = [], [], [], 0, 0
    eng_ok, ind_ok, ind_n, crashes, lat = [], [], 0, 0, []
    per_row = []
    for row in rows:
        rec = by_id[row.id]
        if rec["crash"]:
            crashes += 1
            intent_pairs.append((row.expected_intent, "CRASH"))
            tool_ok.append(False)
            per_row.append({"id": row.id, "crash": rec["crash"]})
            continue
        lat.append(rec["ms"])
        pred_tool = rec["tools"][0]["tool"] if rec["tools"] else "final_answer"
        intent_pairs.append((row.expected_intent, rec["intent"]))
        ok_tool = pred_tool == row.expected_tool
        tool_ok.append(ok_tool)
        exp = {k: v for k, v in row.expected_args.items() if k in SLOTS}
        first = rec["tools"][0] if rec["tools"] else None
        got = predicted_slots(first) if ok_tool else {}
        if "unit_unknown" in row.expected_args:
            got.pop("quantity_kg", None)  # an unknown unit must never become a guessed quantity
        if exp or got:
            slot_items.append((exp, got))
        if row.must_refuse:
            ref_n += 1
            good = is_refusal_ok(row, rec)
            ref_ok += good
        eng_ok.append(rec["error_code"] not in NUMBER_ERRORS)
        g = numbers_grounded(rec) if rec.get("tool_envelopes") else None
        if g is not None:
            ind_n += 1
            ind_ok.append(g)
        per_row.append({"id": row.id, "expected_intent": row.expected_intent, "got_intent": rec["intent"],
                        "expected_tool": row.expected_tool, "got_tool": pred_tool, "error_code": rec["error_code"],
                        "ok": bool(ok_tool and rec["intent"] == row.expected_intent)})
    f1, per_intent = macro_f1(intent_pairs)
    pct = lambda xs: round(sum(xs) / len(xs), 4) if xs else None  # noqa: E731
    p95 = round(sorted(lat)[min(len(lat) - 1, int(round(0.95 * (len(lat) - 1))))], 1) if lat else None
    return {"n": len(rows), "crashes": crashes,
            "intent_macro_f1": f1, "per_intent": per_intent, "confusion": confusion(intent_pairs),
            "tool_accuracy": pct(tool_ok), "slot": slot_f1(slot_items),
            "refusal_compliance": {"n": ref_n, "passed": ref_ok, "rate": round(ref_ok / ref_n, 4) if ref_n else None},
            "number_check": {"engine_level_pass_rate": pct(eng_ok),
                             "final_reply_grounded_rate": pct(ind_ok), "final_replies_with_numbers": ind_n},
            "turn_latency_ms": {"median": round(statistics.median(lat), 1) if lat else None, "p95": p95},
            "failures": [r for r in per_row if not r.get("ok", False)]}


def build_engine(llm_kind: str):
    from app.agents.memory import SessionMemoryStore
    from app.engines.agent_engine import AgentEngine
    if llm_kind == "baseline":
        return AgentEngine(llm_client=RuleBasedLLM(), memory=SessionMemoryStore(FakeRedis()))
    return AgentEngine(memory=SessionMemoryStore(FakeRedis()))  # live provider chain from env


async def evaluate_once(rows: list[EvalRow], llm_kind: str, translate: str, pivot: str, real_rag: bool, tag: str) -> dict:
    prev_pivot = os.environ.get("TRANSLATE_PIVOT")
    os.environ["TRANSLATE_PIVOT"] = pivot
    engine = build_engine(llm_kind)
    rec = install_recorder(real_rag)
    recs = []
    try:
        for row in rows:
            recs.append(await run_conversation(engine, rec, row, translate=translate, tag=f"{tag}_{pivot}"))
    finally:
        import app.engines.agent_engine as eng
        eng.execute_agent_tool = rec.real
        if prev_pivot is None:
            os.environ.pop("TRANSLATE_PIVOT", None)
        else:
            os.environ["TRANSLATE_PIVOT"] = prev_pivot
    return {"pivot": pivot, "translate": translate, "llm": llm_kind, "metrics": score(rows, recs), "records": recs}


def load_rows(path: Path, split: str) -> list[EvalRow]:
    rows = [EvalRow(**json.loads(x)) for x in path.read_text("utf-8").splitlines() if x.strip()]
    return rows if split == "all" else [r for r in rows if r.split == split]


def main() -> None:
    ap = argparse.ArgumentParser()
    ap.add_argument("--set", type=Path, default=DEFAULT_SET)
    ap.add_argument("--split", choices=["dev", "test", "all"], default="test")
    ap.add_argument("--llm", choices=["live", "baseline"], default="live")
    ap.add_argument("--translate", choices=["live", "reference"], default="live",
                    help="live = the engine's own translation (Sarvam when TRANSLATE_BACKEND=sarvam); reference = dataset English")
    ap.add_argument("--pivot", choices=["on", "off", "both"], default="both")
    ap.add_argument("--rag", choices=["fixture", "real"], default="fixture")
    ap.add_argument("--out", type=Path, default=None)
    ap.add_argument("--trace", type=Path, default=None,
                    help="write per-turn records (reply + tool outputs) as JSONL; input for eval_faithfulness.py. "
                         "With --pivot both the pivot setting is appended to the file name.")
    a = ap.parse_args()
    rows = load_rows(a.set, a.split)
    pivots = ["on", "off"] if a.pivot == "both" else [a.pivot]
    runs = [asyncio.run(evaluate_once(rows, a.llm, a.translate, p, a.rag == "real", a.split)) for p in pivots]
    if a.trace:
        for r in runs:
            path = a.trace if len(runs) == 1 else a.trace.with_name(f"{a.trace.stem}_pivot_{r['pivot']}{a.trace.suffix}")
            path.write_text("".join(json.dumps(x, ensure_ascii=False) + "\n" for x in r["records"]), "utf-8")
    for r in runs:
        r.pop("records", None)
    report = {"split": a.split, "runs": runs}
    if a.llm == "baseline":
        report["WARNING"] = "scripted keyword router (not a language model, keyed to this dataset): plumbing check only"
    text = json.dumps(report, ensure_ascii=False, indent=2)
    print(text)
    if a.out:
        a.out.write_text(text + "\n", "utf-8")


if __name__ == "__main__":
    main()
