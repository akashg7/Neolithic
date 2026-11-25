"""Day-2 model bake-off: which LLM drives the agent's tool-calling loop?

    python eval/bakeoff.py --models eval/bakeoff_models.json --data eval/data/bakeoff_40.jsonl \
        --p95-budget-ms 1100

For each candidate and each prompt it simulates one agent turn exactly like the plan's loop:
  system prompt + tools (+ final_answer) -> English message + hints line -> model call(s), a canned
  tool result is fed back, repeat until final_answer (max 3 calls).
Scored per model (decision rule from the plan: fastest model that clears ALL bars):
  tool-selection accuracy  >= 90%   first call must be the expected tool
  argument accuracy        >= 88%   after the wrapper step (names -> IDs, quantity+unit -> kg, hint wins)
  p95 model time per turn  <= budget (sum of the model calls in a turn; default 1100 ms = plan's
                                      'agent: 2 model calls + tools' line)
Also reported: argument accuracy WITHOUT hints (how much the hint rule rescues), refusal rows,
errors, parallel-tool-call attempts.

This harness re-implements the tool schema from the plan table so it runs before Person A's loop
exists. When A's loop is ready, re-run with --loop to use it instead (hook left in `run_turn`).
GRADE assay fields and the navigate whitelist are provisional (see build_bakeoff.py).
"""
from __future__ import annotations

import argparse
import asyncio
import json
import os
import statistics
import sys
import time
from dataclasses import dataclass, field
from datetime import date
from pathlib import Path
from typing import Any, Optional

import httpx

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))
from app.contracts import EvalRow  # noqa: E402
from app.nlp.hints import extract_hints  # noqa: E402
from app.nlp.lexicon import resolve_commodity, resolve_mandi  # noqa: E402
from app.nlp.units import UnknownUnitError, to_kg  # noqa: E402

TOOL_DEFAULTS = {"get_price_forecast": {"horizon_days": 14}, "compute_sale_window": {"grade": "A"}}

SYSTEM_PROMPT = """You are Krishi-Mitr, an assistant for Indian farmers selling crops.
Rules:
- Always answer in English; a separate step translates for the farmer.
- Never state a price, gain, forecast or grade yourself. Call a tool and use its result.
- Use exactly one tool call per step. Pick the tool that matches the farmer's request.
- If a crop, mandi or quantity is missing or unclear, ask a short question with final_answer instead of guessing.
- Give no pesticide or chemical dosage advice; point the farmer to the local Krishi Vigyan Kendra.
- Questions unrelated to farming or this app: say so politely with final_answer.
- When you have what you need, call final_answer.
Hints from the farmer's original words are reliable; prefer them over your own reading."""

PROFILE = "Farmer profile: name Ramesh, district Nashik, crops onion and wheat, 2 active lots, 1 open offer."


def _fn(name: str, desc: str, props: dict, required: list[str]) -> dict:
    return {"type": "function", "function": {"name": name, "description": desc,
            "parameters": {"type": "object", "properties": props, "required": required}}}


S = {"type": "string"}
N = {"type": "number"}
TOOLS = [
    _fn("compute_sale_window", "Sell-or-wait verdict for a quantity of a crop at a mandi. Fetches the forecast itself.",
        {"commodity": S, "mandi": S, "quantity": N, "unit": S, "grade": S}, ["commodity", "mandi", "quantity", "unit"]),
    _fn("get_price_forecast", "Price forecast (p10/p50/p90) for a crop at a mandi.",
        {"commodity": S, "mandi": S, "horizon_days": N}, ["commodity"]),
    _fn("calculate_grade", "Grade a produce lot from its assay values.", {"commodity": S, "assay": {"type": "object"}}, ["commodity"]),
    _fn("create_lot_draft", "Prepare a lot draft card for the farmer to confirm. Never saves.",
        {"commodity": S, "quantity": N, "unit": S, "mandi": S, "expected_price_rupees": N}, ["commodity", "quantity", "unit"]),
    _fn("get_farmer_portfolio", "The farmer's active lots, offers and escrow status.", {}, []),
    _fn("search_agri_knowledge", "Search schemes, grading standards, platform help and glossary.",
        {"query": S, "category": {"type": "string", "enum": ["schemes_finance", "grading", "platform", "glossary"]}, "crop": S}, ["query"]),
    _fn("navigate_screen", "Offer to open an app screen.", {"target_screen": S, "params": {"type": "object"}}, ["target_screen"]),
    _fn("final_answer", "End the turn with the English reply.",
        {"reply_text": S, "intent": {"type": "string", "enum": ["PRICE", "WINDOW", "LOT", "GRADE", "PORTFOLIO", "RAG", "ONBOARD", "NAVIGATE", "SMALLTALK", "OUT_OF_SCOPE"]},
         "quick_replies": {"type": "array", "items": S}}, ["reply_text", "intent"]),
]
STUB_RESULT = json.dumps({"ok": True, "data": {"note": "stub result for bake-off"}, "source": "stub", "card": None, "error": None})


# ---------------------------------------------------------------------------- normalisation (the 'wrapper')
def normalise_args(tool: str, args: dict, hints: Optional[dict]) -> dict:
    """Mirror Person A's wrapper: names -> IDs, quantity+unit -> kg, tool defaults, hint wins."""
    a = dict(TOOL_DEFAULTS.get(tool, {}))
    a.update({k: v for k, v in args.items() if v is not None})
    out: dict[str, Any] = {}
    for k, v in a.items():
        if k == "commodity" and isinstance(v, str):
            out[k] = resolve_commodity(v) or v
        elif k == "crop" and isinstance(v, str):
            out[k] = resolve_commodity(v) or v.lower()
        elif k == "mandi" and isinstance(v, str):
            out[k] = resolve_mandi(v) or v
        elif k in ("quantity", "unit"):
            continue
        elif k == "expected_price_rupees":
            out["expected_price"] = v
        else:
            out[k] = v
    if "quantity" in a and "unit" in a:
        try:
            out["quantity_kg"] = to_kg(float(a["quantity"]), str(a["unit"]))
        except (UnknownUnitError, ValueError, TypeError):
            pass
    if hints:
        for k in ("commodity", "mandi", "quantity_kg"):
            if k in hints and (k in out or tool in ("compute_sale_window", "create_lot_draft", "get_price_forecast")):
                if k == "quantity_kg" and tool == "get_price_forecast":
                    continue
                if k == "mandi" and tool == "create_lot_draft" and "mandi" not in out:
                    continue
                out[k] = hints[k]
    return out


def expected_normalised(row: EvalRow) -> dict:
    e = dict(row.expected_args)
    if isinstance(e.get("crop"), str):
        e["crop"] = resolve_commodity(e["crop"]) or e["crop"].lower()
    return e


def args_correct(expected: dict, got: dict) -> bool:
    return all(got.get(k) == v for k, v in expected.items())


# ---------------------------------------------------------------------------- one turn
@dataclass
class TurnResult:
    row_id: str
    first_tool: Optional[str] = None
    tool_ok: bool = False
    args_ok_hints: bool = False
    args_ok_nohints: bool = False
    calls: int = 0
    call_ms: list[float] = field(default_factory=list)
    parallel_attempt: bool = False
    error: Optional[str] = None

    @property
    def turn_ms(self) -> float:
        return sum(self.call_ms)


async def chat(client: httpx.AsyncClient, cand: dict, messages: list[dict], tool_choice: str) -> tuple[dict, float]:
    body = {"model": cand["model"], "messages": messages, "tools": TOOLS, "tool_choice": tool_choice,
            "temperature": 0.2, **cand.get("extra", {})}
    t0 = time.perf_counter()
    r = await client.post(cand["base_url"].rstrip("/") + "/chat/completions", json=body,
                          headers={"Authorization": f"Bearer {os.getenv(cand['api_key_env'], '')}"}, timeout=30)
    ms = (time.perf_counter() - t0) * 1000
    r.raise_for_status()
    return r.json(), ms


async def run_turn(client: httpx.AsyncClient, cand: dict, row: EvalRow) -> TurnResult:
    res = TurnResult(row.id)
    hints = extract_hints(row.turns_original[0])
    hint_line = "Hints from the farmer's original words: " + (", ".join(f"{k}={v}" for k, v in hints.items()) or "none")
    messages: list[dict] = [
        {"role": "system", "content": SYSTEM_PROMPT},
        {"role": "system", "content": f"{PROFILE} Screen: home. Today: {date.today().isoformat()}."},
        {"role": "user", "content": f"{row.turns_english[-1]}\n{hint_line}"},
    ]
    tool_choice = cand.get("tool_choice", "required")
    try:
        for step in range(3):
            data, ms = await chat(client, cand, messages, tool_choice)
            res.calls += 1
            res.call_ms.append(ms)
            msg = data["choices"][0]["message"]
            calls = msg.get("tool_calls") or []
            if not calls:
                break  # model replied in plain text; counts as no tool call
            if step == 0:
                res.parallel_attempt = len(calls) > 1
                name = calls[0]["function"]["name"]
                try:
                    raw = json.loads(calls[0]["function"].get("arguments") or "{}")
                except json.JSONDecodeError:
                    raw = {}
                res.first_tool = name
                res.tool_ok = name == row.expected_tool
                if res.tool_ok:
                    exp = expected_normalised(row)
                    res.args_ok_hints = args_correct(exp, normalise_args(name, raw, hints))
                    res.args_ok_nohints = args_correct(exp, normalise_args(name, raw, None))
            if calls[0]["function"]["name"] == "final_answer":
                break
            messages.append({"role": "assistant", "content": msg.get("content"), "tool_calls": calls})
            for c in calls:
                messages.append({"role": "tool", "tool_call_id": c["id"], "content": STUB_RESULT})
    except Exception as e:  # network, 4xx/5xx, malformed JSON: record, keep going
        res.error = f"{type(e).__name__}: {str(e)[:160]}"
    return res


async def run_turn_agent_loop(cand: dict, row: EvalRow) -> TurnResult:
    """Run one bake-off row using Person A's real system prompt, context builder,
    canonical tool schemas, and `OpenAICompatibleLLMClient`."""
    from app.agents.context import build_context_messages
    from app.agents.llm_client import OpenAICompatibleLLMClient, ProviderConfig
    from app.agents.tool_bridge import agent_tool_schemas
    from app.schemas.agent import ScreenContext

    res = TurnResult(row.id)
    hints = extract_hints(row.turns_original[0])
    messages = build_context_messages(
        profile_block=PROFILE,
        history_turns=[],
        screen_context=ScreenContext(
            current_screen=(row.screen_context or {}).get("current_screen") or "home",
            active_commodity_id=(row.screen_context or {}).get("active_commodity_id"),
            active_market_id=(row.screen_context or {}).get("active_market_id"),
            active_lot_id=(row.screen_context or {}).get("active_lot_id"),
        ),
        model_input_text=row.turns_english[-1],
        hints=hints,
        pivot_on=True,
        target_lang="en",
    )
    cfg = ProviderConfig(
        name=cand["name"],
        base_url=cand["base_url"],
        api_key=os.getenv(cand["api_key_env"], ""),
        model=cand["model"],
        extra=dict(cand.get("extra") or {}),
    )
    llm = OpenAICompatibleLLMClient([cfg])
    tools = agent_tool_schemas()
    tool_choice = cand.get("tool_choice", "required")
    try:
        for step in range(3):
            resp = await llm.complete(messages, tools=tools, temperature=0.2, tool_choice=tool_choice)
            res.calls += 1
            res.call_ms.append(resp.latency_ms)
            calls = resp.tool_calls
            if not calls:
                break
            if step == 0:
                res.parallel_attempt = len(calls) > 1
                name = calls[0].name
                res.first_tool = name
                res.tool_ok = name == row.expected_tool
                if res.tool_ok:
                    exp = expected_normalised(row)
                    res.args_ok_hints = args_correct(exp, normalise_args(name, calls[0].arguments, hints))
                    res.args_ok_nohints = args_correct(exp, normalise_args(name, calls[0].arguments, None))
            if calls[0].name == "final_answer":
                break
            messages.append({
                "role": "assistant",
                "content": resp.content,
                "tool_calls": [
                    {"id": c.id, "type": "function", "function": {"name": c.name, "arguments": c.raw_arguments}}
                    for c in calls
                ],
            })
            for c in calls:
                messages.append({"role": "tool", "tool_call_id": c.id, "content": STUB_RESULT})
    except Exception as e:
        res.error = f"{type(e).__name__}: {str(e)[:160]}"
    return res


# ---------------------------------------------------------------------------- scoring + decision
def pct(xs: list[bool]) -> float:
    return round(100 * sum(xs) / len(xs), 1) if xs else 0.0


def p95(xs: list[float]) -> float:
    if not xs:
        return float("nan")
    s = sorted(xs)
    return round(s[min(len(s) - 1, int(round(0.95 * (len(s) - 1))))], 1)


def summarise(cand: dict, rows: list[EvalRow], results: list[TurnResult], budget_ms: float) -> dict:
    ok_turns = [r for r in results if r.error is None]
    needs_args = [r for r, row in zip(results, rows) if row.expected_args]
    s = {
        "model": cand["name"], "model_id": cand["model"], "n": len(results), "errors": len(results) - len(ok_turns),
        "tool_accuracy": pct([r.tool_ok for r in results]),
        "args_accuracy_with_hints": pct([r.args_ok_hints for r in needs_args]),
        "args_accuracy_model_only": pct([r.args_ok_nohints for r in needs_args]),
        "refusal_rows_correct": pct([r.tool_ok for r, row in zip(results, rows) if row.must_refuse]),
        "single_call_p50_ms": round(statistics.median([m for r in ok_turns for m in r.call_ms]), 1) if ok_turns else None,
        "single_call_p95_ms": p95([m for r in ok_turns for m in r.call_ms]),
        "turn_p50_ms": round(statistics.median([r.turn_ms for r in ok_turns]), 1) if ok_turns else None,
        "turn_p95_ms": p95([r.turn_ms for r in ok_turns]),
        "parallel_tool_call_attempts": sum(r.parallel_attempt for r in results),
        "failed_ids": [r.row_id for r in results if not r.tool_ok or r.error],
    }
    s["bars"] = {"tool>=90": s["tool_accuracy"] >= 90, "args>=88": s["args_accuracy_with_hints"] >= 88,
                 f"p95_turn<={budget_ms:.0f}ms": s["turn_p95_ms"] == s["turn_p95_ms"] and s["turn_p95_ms"] <= budget_ms,
                 "no_errors": s["errors"] == 0}
    s["passes_all"] = all(s["bars"].values())
    return s


def decide(summaries: list[dict]) -> Optional[str]:
    passing = [s for s in summaries if s["passes_all"]]
    return min(passing, key=lambda s: s["turn_p95_ms"])["model"] if passing else None


def markdown(summaries: list[dict], winner: Optional[str], budget_ms: float) -> str:
    h = "| model | tool % | args % (hints) | args % (model only) | refusals % | call p95 ms | turn p95 ms | errors | pass |\n|---|---|---|---|---|---|---|---|---|\n"
    for s in summaries:
        h += (f"| {s['model']} | {s['tool_accuracy']} | {s['args_accuracy_with_hints']} | {s['args_accuracy_model_only']} | "
              f"{s['refusal_rows_correct']} | {s['single_call_p95_ms']} | {s['turn_p95_ms']} | {s['errors']} | {'YES' if s['passes_all'] else 'no'} |\n")
    h += f"\nBars: tool >= 90, args >= 88, turn p95 <= {budget_ms:.0f} ms, no errors. "
    h += f"**Winner (fastest passing): {winner}**\n" if winner else "**No model passed all bars. Do not silently relax them: pick per the plan's fallback rule and record why.**\n"
    return h


async def main_async(a: argparse.Namespace) -> None:
    rows = [EvalRow(**json.loads(x)) for x in Path(a.data).read_text("utf-8").splitlines() if x.strip()]
    cands = json.loads(Path(a.models).read_text("utf-8"))["candidates"]
    cands = [c for c in cands if not c["model"].startswith("REPLACE_") and os.getenv(c["api_key_env"])]
    if not cands:
        sys.exit("No runnable candidates: set the API key env vars and replace REPLACE_* model ids in the models file.")
    summaries = []
    async with httpx.AsyncClient() as client:
        for cand in cands:
            print(f"== {cand['name']} ({cand['model']})", flush=True)
            if getattr(a, "loop", False):
                results = [await run_turn_agent_loop(cand, row) for row in rows]
            else:
                results = [await run_turn(client, cand, row) for row in rows]  # sequential: fair latency
            summaries.append(summarise(cand, rows, results, a.p95_budget_ms))
    winner = decide(summaries)
    out_dir = ROOT / "eval/results"
    out_dir.mkdir(exist_ok=True)
    stamp = time.strftime("%Y%m%d-%H%M%S")
    (out_dir / f"bakeoff_{stamp}.json").write_text(json.dumps({"summaries": summaries, "winner": winner}, indent=1), "utf-8")
    md = markdown(summaries, winner, a.p95_budget_ms)
    (out_dir / f"bakeoff_{stamp}.md").write_text(md, "utf-8")
    print(md)


def main() -> None:
    ap = argparse.ArgumentParser()
    ap.add_argument("--models", default=str(ROOT / "eval/bakeoff_models.json"))
    ap.add_argument("--data", default=str(ROOT / "eval/data/bakeoff_40.jsonl"))
    ap.add_argument("--p95-budget-ms", type=float, default=1100.0)
    ap.add_argument("--loop", action="store_true", help="Run via Person A's real agent context, tool schemas, and OpenAI-SDK client.")
    asyncio.run(main_async(ap.parse_args()))


if __name__ == "__main__":
    main()
