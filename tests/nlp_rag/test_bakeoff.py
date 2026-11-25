import asyncio
import json
from pathlib import Path

import httpx

from eval import bakeoff as B
from app.contracts import EvalRow

ROWS = [EvalRow(**json.loads(x)) for x in
        (Path(B.ROOT) / "eval/data/bakeoff_40.jsonl").read_text("utf-8").splitlines()]
CAND = {"name": "mock", "model": "mock-1", "base_url": "http://mock/v1", "api_key_env": "MOCK_KEY", "extra": {}}


def tool_call(name, args, cid="c1"):
    return {"id": cid, "type": "function", "function": {"name": name, "arguments": json.dumps(args)}}


def completion(calls):
    return {"choices": [{"message": {"role": "assistant", "content": None, "tool_calls": calls}}]}


def oracle_args(row: EvalRow) -> dict:
    e = row.expected_args
    a = {}
    if "commodity" in e: a["commodity"] = e["commodity"]
    if "mandi" in e: a["mandi"] = e["mandi"]
    if "quantity_kg" in e: a.update(quantity=e["quantity_kg"], unit="kg")
    if "horizon_days" in e: a["horizon_days"] = e["horizon_days"]
    if "expected_price" in e: a["expected_price_rupees"] = e["expected_price"]
    for k in ("category", "crop", "target_screen"):
        if k in e: a[k] = e[k]
    if row.expected_tool == "search_agri_knowledge": a["query"] = row.turns_english[0]
    if row.expected_tool == "final_answer": a.update(reply_text="ok", intent=row.expected_intent)
    return a


def make_transport(policy):
    """policy(row, step, body) -> list of tool_calls"""
    def handler(request: httpx.Request):
        body = json.loads(request.content)
        user = next(m["content"] for m in body["messages"] if m["role"] == "user")
        row = next(r for r in ROWS if user.startswith(r.turns_english[0]))  # duplicates share expectations
        step = sum(m["role"] == "tool" for m in body["messages"])  # stateless: tool results so far
        return httpx.Response(200, json=completion(policy(row, step, body)))

    return httpx.MockTransport(handler)


def run_all(policy):
    async def go():
        async with httpx.AsyncClient(transport=make_transport(policy)) as c:
            return [await B.run_turn(c, CAND, r) for r in ROWS]
    return asyncio.run(go())


def oracle(row, step, body):
    if step == 0 and row.expected_tool != "final_answer":
        return [tool_call(row.expected_tool, oracle_args(row))]
    return [tool_call("final_answer", {"reply_text": "done", "intent": row.expected_intent})]


def test_oracle_model_scores_100(monkeypatch):
    monkeypatch.setenv("MOCK_KEY", "k")
    res = run_all(oracle)
    s = B.summarise(CAND, ROWS, res, 1100)
    assert s["tool_accuracy"] == 100 and s["args_accuracy_with_hints"] == 100 and s["errors"] == 0
    assert s["passes_all"] and B.decide([s]) == "mock"
    assert all(r.calls == (1 if row.expected_tool == "final_answer" else 2) for r, row in zip(res, ROWS))


def test_hint_rescues_wrong_model_commodity(monkeypatch):
    monkeypatch.setenv("MOCK_KEY", "k")

    def wrong_commodity(row, step, body):
        calls = oracle(row, step, body)
        if step == 0 and "commodity" in row.expected_args and row.expected_tool != "final_answer":
            args = json.loads(calls[0]["function"]["arguments"])
            args["commodity"] = "cmd_banana"
            calls = [tool_call(row.expected_tool, args)]
        return calls

    s = B.summarise(CAND, ROWS, run_all(wrong_commodity), 1100)
    assert s["args_accuracy_model_only"] < 40          # model alone is wrong where a commodity is expected
    assert s["args_accuracy_with_hints"] > s["args_accuracy_model_only"] + 30  # hints from the original text rescue most
    assert s["tool_accuracy"] == 100


def test_wrong_tool_fails_the_bar_and_blocks_selection(monkeypatch):
    monkeypatch.setenv("MOCK_KEY", "k")
    bad = lambda row, step, body: [tool_call("get_farmer_portfolio", {})] if step == 0 else oracle(row, 1, body)
    s = B.summarise(CAND, ROWS, run_all(bad), 1100)
    assert s["tool_accuracy"] < 90 and not s["passes_all"] and B.decide([s]) is None


def test_parallel_tool_calls_are_counted(monkeypatch):
    monkeypatch.setenv("MOCK_KEY", "k")
    par = lambda row, step, body: ([tool_call(row.expected_tool, oracle_args(row), "a"), tool_call("get_farmer_portfolio", {}, "b")]
                                   if step == 0 and row.expected_tool != "final_answer" else oracle(row, step, body))
    s = B.summarise(CAND, ROWS, run_all(par), 1100)
    assert s["parallel_tool_call_attempts"] > 20 and s["tool_accuracy"] == 100


def test_http_errors_are_recorded_not_raised(monkeypatch):
    monkeypatch.setenv("MOCK_KEY", "k")

    async def go():
        t = httpx.MockTransport(lambda r: httpx.Response(429))
        async with httpx.AsyncClient(transport=t) as c:
            return await B.run_turn(c, CAND, ROWS[0])

    r = asyncio.run(go())
    assert r.error and not r.tool_ok


def test_decision_picks_fastest_passing_model():
    mk = lambda name, p95, ok: {"model": name, "turn_p95_ms": p95, "passes_all": ok}
    assert B.decide([mk("a", 900, True), mk("b", 600, True), mk("c", 300, False)]) == "b"
    assert B.decide([mk("a", 900, False)]) is None


def test_normalise_args_wrapper_semantics():
    n = B.normalise_args
    assert n("compute_sale_window", {"commodity": "कांदा", "mandi": "Lasalgaon", "quantity": 20, "unit": "bori"}, None) == \
        {"commodity": "cmd_onion", "mandi": "mkt_lasalgaon", "grade": "A", "quantity_kg": 1000}
    # hint wins over a wrong model argument
    got = n("compute_sale_window", {"commodity": "tomato", "mandi": "pune", "quantity": 5, "unit": "kg"},
            {"commodity": "cmd_onion", "mandi": "mkt_lasalgaon", "quantity_kg": 1000})
    assert got["commodity"] == "cmd_onion" and got["mandi"] == "mkt_lasalgaon" and got["quantity_kg"] == 1000
    # variable-size unit: no kg is invented
    assert "quantity_kg" not in n("create_lot_draft", {"commodity": "cotton", "quantity": 10, "unit": "khandi"}, None)
    # price forecast default horizon
    assert n("get_price_forecast", {"commodity": "onion"}, None)["horizon_days"] == 14
