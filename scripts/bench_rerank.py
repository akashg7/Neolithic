"""Rerank latency benchmark -> the keep/drop decision for bge-reranker-v2-m3 on CPU.

Plan rule: drop the reranker if it adds more than ~300 ms per query. Run on the machine that will serve
(or the demo laptop), after `scripts/ingest_rag.py` has filled Qdrant:

    python scripts/bench_rerank.py --split dev --out eval/results/rerank_latency.json

Measures the SAME queries twice (reranker off, then on) so the delta is the reranker's own cost, and also
reports hit@5 both ways so "slower but not better" is visible too. One warm-up query is discarded.
"""
from __future__ import annotations

import argparse
import json
import statistics
import sys
import time
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))
from eval import eval_rag as er  # noqa: E402

BUDGET_MS = 300.0


def pct(xs: list[float], q: float) -> float:
    s = sorted(xs)
    return s[min(len(s) - 1, int(round(q * (len(s) - 1))))]


def timed(rows, retriever, query: str) -> tuple[list[float], dict]:
    ms = []
    for r in rows:
        text = (r.turns_english if query == "english" else r.turns_original)[0]
        t0 = time.perf_counter()
        retriever.search_sync(text, locale=r.locale, k=er.K_MRR)
        ms.append((time.perf_counter() - t0) * 1000)
    return ms, er.evaluate(rows, retriever, query)["overall"]


def decide(delta_median_ms: float, delta_p95_ms: float, budget_ms: float = BUDGET_MS) -> str:
    return "KEEP" if max(delta_median_ms, delta_p95_ms) <= budget_ms else "DROP"


def main() -> None:
    ap = argparse.ArgumentParser()
    ap.add_argument("--set", type=Path, default=er.DEFAULT_SET)
    ap.add_argument("--split", choices=["dev", "test", "all"], default="dev")
    ap.add_argument("--query", choices=["original", "english"], default="original")
    ap.add_argument("--embedder", choices=["bge-m3", "fake"], default="bge-m3")
    ap.add_argument("--qdrant-url", default="http://localhost:6333")
    ap.add_argument("--collection", default="krishi_mitr_kb")
    ap.add_argument("--budget-ms", type=float, default=BUDGET_MS)
    ap.add_argument("--out", type=Path, default=None)
    a = ap.parse_args()
    a.ingest_memory = False
    rows = [r for r in er.load_rows(a.set, a.split) if not r.must_refuse]
    retriever = er.build_retriever(a)
    retriever.search_sync(rows[0].turns_original[0], k=er.K_MRR)            # warm-up (model load, caches)
    base_ms, base_q = timed(rows, retriever, a.query)
    retriever.reranker = er.load_reranker()
    retriever.search_sync(rows[0].turns_original[0], k=er.K_MRR)            # warm-up the reranker too
    rr_ms, rr_q = timed(rows, retriever, a.query)
    d_med = statistics.median(rr_ms) - statistics.median(base_ms)
    d_p95 = pct(rr_ms, 0.95) - pct(base_ms, 0.95)
    out = {"split": a.split, "query": a.query, "n": len(rows), "budget_ms": a.budget_ms,
           "without_rerank": {"median_ms": round(statistics.median(base_ms), 1), "p95_ms": round(pct(base_ms, .95), 1), **base_q},
           "with_rerank": {"median_ms": round(statistics.median(rr_ms), 1), "p95_ms": round(pct(rr_ms, .95), 1), **rr_q},
           "added_median_ms": round(d_med, 1), "added_p95_ms": round(d_p95, 1),
           "decision": decide(d_med, d_p95, a.budget_ms),
           "note": "decision is on latency only; check the hit@5/MRR delta before keeping a slow reranker"}
    text = json.dumps(out, indent=2)
    print(text)
    if a.out:
        a.out.parent.mkdir(parents=True, exist_ok=True)
        a.out.write_text(text + "\n")


if __name__ == "__main__":
    main()
