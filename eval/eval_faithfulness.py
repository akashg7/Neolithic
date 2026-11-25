"""Cross-provider faithfulness judge: does every claim in an agent reply follow from the tool outputs?

    python eval/eval_agent.py --split test --llm live --pivot on --trace eval/results/agent_trace.jsonl
    python eval/eval_faithfulness.py --trace eval/results/agent_trace.jsonl \
        --agent-provider groq --judge-provider gemini --out eval/results/faithfulness_test.json

The judge MUST be a different provider from the agent (a model grading its own family flatters it);
the script refuses to run when they match. A reply is judged against the SOURCES only (the tool
outputs of that turn: window verdict, price snapshot, grade, retrieved chunks), never against the
judge's own knowledge. Replies that are fixed refusal/fallback templates carry no claims and are skipped.

Reported:  reply-level faithful rate (no unsupported/contradicted claim), claim-level supported rate,
and the list of unfaithful replies. The judge sees the localized reply (it is what the farmer reads).
"""
from __future__ import annotations

import argparse
import asyncio
import json
import re
import sys
from pathlib import Path
from typing import Awaitable, Callable, Optional

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))

SYSTEM = """You are a strict fact-checker for a farmer-advice assistant.
You get SOURCES (JSON tool outputs) and a REPLY. Split the REPLY into atomic factual claims (prices,
amounts, days, grades, rules, loan terms, names). Ignore greetings, questions and polite filler.
Money in SOURCES is in paise (100 paise = 1 rupee); kg may be shown as quintals (100 kg) or bori (50 kg).
For each claim answer exactly one verdict:
  supported     the SOURCES state it, or it follows by those unit conversions
  unsupported   the SOURCES do not contain it
  contradicted  the SOURCES say something different
Judge ONLY from SOURCES, never from your own knowledge. The REPLY may be in Marathi or Hindi.
Reply with JSON only: {"claims":[{"claim":"...","verdict":"supported|unsupported|contradicted"}]}"""

Judge = Callable[[str, str], Awaitable[str]]  # (system, user) -> raw model text


def load_records(paths: list[Path]) -> list[dict]:
    out = []
    for p in paths:
        out += [json.loads(x) for x in p.read_text("utf-8").splitlines() if x.strip()]
    return out


def is_judgeable(rec: dict) -> bool:
    """Needs a real reply grounded in at least one successful tool result; fixed templates are skipped."""
    from app.nlp.messages import MESSAGES
    if rec.get("crash") or not rec.get("reply") or not rec.get("tool_envelopes"):
        return False
    if rec.get("error_code") in ("NO_ADVICE", "CHEMICAL_ADVICE_REFUSED", "FALLBACK", "GUARD_FALLBACK", "NUMBER_CHECK_FAILED"):
        return False
    if any(rec["reply"] in m.values() for m in MESSAGES.values()):
        return False
    return any(t["envelope"].get("ok") for t in rec["tool_envelopes"])


def build_user_prompt(rec: dict) -> str:
    sources = [{"tool": t["tool"], "data": t["envelope"].get("data"), "card": t["envelope"].get("card")}
               for t in rec["tool_envelopes"] if t["envelope"].get("ok")]
    return f"SOURCES:\n{json.dumps(sources, ensure_ascii=False)[:6000]}\n\nREPLY:\n{rec['reply']}"


def parse_verdicts(raw: str) -> list[dict]:
    text = re.sub(r"^```(?:json)?|```$", "", raw.strip(), flags=re.MULTILINE).strip()
    m = re.search(r"\{.*\}", text, flags=re.DOTALL)
    if not m:
        raise ValueError("judge returned no JSON object")
    claims = json.loads(m.group(0)).get("claims")
    if not isinstance(claims, list):
        raise ValueError("judge JSON has no 'claims' list")
    ok = {"supported", "unsupported", "contradicted"}
    return [{"claim": str(c.get("claim", "")), "verdict": str(c.get("verdict", "")).lower()} for c in claims
            if str(c.get("verdict", "")).lower() in ok]


async def judge_records(records: list[dict], judge: Judge) -> dict:
    judged, errors, claims_total, claims_ok = [], [], 0, 0
    for rec in records:
        if not is_judgeable(rec):
            continue
        try:
            verdicts = parse_verdicts(await judge(SYSTEM, build_user_prompt(rec)))
        except Exception as e:
            errors.append({"id": rec["id"], "error": f"{type(e).__name__}: {str(e)[:120]}"})
            continue
        bad = [v for v in verdicts if v["verdict"] != "supported"]
        claims_total += len(verdicts)
        claims_ok += len(verdicts) - len(bad)
        judged.append({"id": rec["id"], "n_claims": len(verdicts), "faithful": not bad and len(verdicts) > 0,
                       "problems": bad, "reply": rec["reply"]})
    n = len(judged)
    return {"replies_judged": n, "judge_errors": len(errors),
            "reply_faithful_rate": round(sum(j["faithful"] for j in judged) / n, 4) if n else None,
            "claims_judged": claims_total,
            "claim_supported_rate": round(claims_ok / claims_total, 4) if claims_total else None,
            "unfaithful": [j for j in judged if not j["faithful"]], "errors": errors}


def make_live_judge(provider: str, model: Optional[str]) -> Judge:
    from app.agents.llm_client import OpenAICompatibleLLMClient, ProviderConfig, _provider_defaults
    cfg = _provider_defaults(provider)
    if cfg is None or not cfg.api_key:
        sys.exit(f"judge provider {provider!r} has no API key configured in the environment/.env")
    if model:
        cfg = ProviderConfig(name=cfg.name, base_url=cfg.base_url, api_key=cfg.api_key, model=model, extra={})
    client = OpenAICompatibleLLMClient([cfg])

    async def judge(system: str, user: str) -> str:
        resp = await client.complete([{"role": "system", "content": system}, {"role": "user", "content": user}],
                                     tools=None, temperature=0.0, tool_choice="none")
        return resp.content or ""
    judge.model = cfg.model  # type: ignore[attr-defined]
    return judge


def main() -> None:
    ap = argparse.ArgumentParser()
    ap.add_argument("--trace", type=Path, nargs="+", required=True)
    ap.add_argument("--agent-provider", required=True, help="provider that produced the replies (e.g. groq)")
    ap.add_argument("--judge-provider", required=True, help="a DIFFERENT provider (e.g. gemini or openai)")
    ap.add_argument("--judge-model", default=None)
    ap.add_argument("--out", type=Path, default=None)
    a = ap.parse_args()
    if a.agent_provider.strip().lower() == a.judge_provider.strip().lower():
        sys.exit("judge provider must differ from the agent provider")
    judge = make_live_judge(a.judge_provider, a.judge_model)
    report = {"agent_provider": a.agent_provider, "judge_provider": a.judge_provider, "judge_model": judge.model,
              "result": asyncio.run(judge_records(load_records(a.trace), judge))}
    text = json.dumps(report, ensure_ascii=False, indent=2)
    print(text)
    if a.out:
        a.out.write_text(text + "\n", "utf-8")


if __name__ == "__main__":
    main()
