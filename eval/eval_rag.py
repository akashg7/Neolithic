"""Retrieval quality on the RAG benchmark: Hit@5, Recall@5, MRR@10 (+ ablations).

    # real numbers (needs the BGE-M3 model + a Qdrant that has the corpus ingested):
    python eval/eval_rag.py --split test --embedder bge-m3 --qdrant-url http://localhost:6333 --ablate
    # add the reranker row:
    python eval/eval_rag.py --split test --embedder bge-m3 --qdrant-url http://localhost:6333 --ablate --rerank
    # offline plumbing check ONLY (hash embeddings: the numbers mean nothing about quality):
    python eval/eval_rag.py --split dev --embedder fake --ingest-memory --ablate

Definitions (answerable rows only; must_refuse rows are excluded and reported separately):
  Hit@5     1 if any expected chunk is in the top 5, else 0.
  Recall@5  |expected chunks found in top 5| / |expected chunks|.
  MRR@10    1 / rank of the first expected chunk within the top 10, else 0.
Queries are the ORIGINAL-language text by default (`--query english` uses the translated turn).
Retrieval is unfiltered unless --category-filter is given (then the row's expected category is passed,
which is how the agent behaves when the model picks a category).
Report the TEST split in the final numbers; tune on dev.
"""
from __future__ import annotations

import argparse
import json
import statistics
import sys
import warnings
from collections import defaultdict
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))
from app.contracts import EvalRow  # noqa: E402

warnings.filterwarnings("ignore", message="Payload indexes have no effect")
DEFAULT_SET = ROOT / "eval/data/rag_bench.jsonl"
K_HIT, K_MRR = 5, 10


def load_rows(path: Path, split: str) -> list[EvalRow]:
    rows = [EvalRow(**json.loads(x)) for x in path.read_text("utf-8").splitlines() if x.strip()]
    return rows if split == "all" else [r for r in rows if r.split == split]


def score_row(expected: list[str], ranked_ids: list[str]) -> dict:
    exp = set(expected)
    top5 = ranked_ids[:K_HIT]
    found = exp & set(top5)
    rr = 0.0
    for rank, cid in enumerate(ranked_ids[:K_MRR], start=1):
        if cid in exp:
            rr = 1.0 / rank
            break
    return {"hit": 1.0 if found else 0.0, "recall": len(found) / len(exp), "rr": rr}


def aggregate(scored: list[dict]) -> dict:
    n = len(scored)
    if not n:
        return {"n": 0, "hit@5": None, "recall@5": None, "mrr@10": None}
    return {"n": n,
            "hit@5": round(sum(s["hit"] for s in scored) / n, 4),
            "recall@5": round(sum(s["recall"] for s in scored) / n, 4),
            "mrr@10": round(sum(s["rr"] for s in scored) / n, 4)}


def evaluate(rows: list[EvalRow], retriever, query: str = "original", use_category: bool = False) -> dict:
    """Run every answerable row through `retriever.search_sync`; refusal rows only contribute top scores."""
    scored, by_locale, by_category = [], defaultdict(list), defaultdict(list)
    misses, ans_top, refuse_top = [], [], []
    for r in rows:
        text = (r.turns_english if query == "english" else r.turns_original)[0]
        category = r.expected_args.get("category") if use_category else None
        chunks = retriever.search_sync(text, locale=r.locale, category=category, k=K_MRR)
        if r.must_refuse:
            refuse_top.append(chunks[0].score if chunks else 0.0)
            continue
        s = score_row(r.expected_chunk_ids, [c.chunk_id for c in chunks])
        scored.append(s)
        by_locale[r.locale].append(s)
        by_category[r.expected_args.get("category") or "none"].append(s)
        ans_top.append(chunks[0].score if chunks else 0.0)
        if not s["hit"]:
            misses.append({"id": r.id, "text": text, "expected": r.expected_chunk_ids,
                           "got_top3": [c.chunk_id for c in chunks[:3]]})
    med = lambda xs: round(statistics.median(xs), 4) if xs else None  # noqa: E731
    return {"overall": aggregate(scored),
            "by_locale": {k: aggregate(v) for k, v in sorted(by_locale.items())},
            "by_category": {k: aggregate(v) for k, v in sorted(by_category.items())},
            "refusal_rows": {"n": len(refuse_top), "median_top1_score": med(refuse_top),
                             "answerable_median_top1_score": med(ans_top)},
            "misses": misses}


def ablation(rows: list[EvalRow], retriever, with_rerank: bool, use_category: bool) -> dict:
    """mode (dense | sparse | hybrid) x query language (original | english), plus hybrid+rerank."""
    out, base_mode, base_rerank = {}, retriever.mode, retriever.reranker
    retriever.reranker = None
    try:
        for mode in ("dense", "sparse", "hybrid"):
            retriever.mode = mode
            for q in ("original", "english"):
                out[f"{mode}/{q}"] = evaluate(rows, retriever, q, use_category)["overall"]
        if with_rerank:
            retriever.mode = "hybrid"
            retriever.reranker = load_reranker()
            for q in ("original", "english"):
                out[f"hybrid+rerank/{q}"] = evaluate(rows, retriever, q, use_category)["overall"]
    finally:
        retriever.mode, retriever.reranker = base_mode, base_rerank
    return out


def load_reranker():
    from FlagEmbedding import FlagReranker
    import os
    return FlagReranker(os.getenv("RERANK_MODEL", "BAAI/bge-reranker-v2-m3"), use_fp16=False)


def build_retriever(args):
    from app.rag import store
    from app.rag.chunker import approx_token_counter, bge_m3_token_counter
    from app.rag.embedder import make_embedder
    from app.rag.qdrant_retriever import Retriever
    import os
    os.environ["EMBEDDER"] = args.embedder
    emb = make_embedder()
    if args.ingest_memory:
        import importlib.util
        spec = importlib.util.spec_from_file_location("ingest_rag", ROOT / "scripts/ingest_rag.py")
        ing = importlib.util.module_from_spec(spec)
        spec.loader.exec_module(ing)
        client = store.connect(":memory:")
        store.ensure_collection(client, args.collection, emb.dense_dim)
        count = approx_token_counter if args.embedder == "fake" else bge_m3_token_counter()
        ing.ingest(ROOT / "data/rag_corpus", client, args.collection, emb, count)
    else:
        client = store.connect(args.qdrant_url)
        if not client.collection_exists(args.collection):
            raise SystemExit(f"collection {args.collection!r} not found at {args.qdrant_url}; run scripts/ingest_rag.py first")
    return Retriever(client=client, collection=args.collection, embedder=emb, reranker=None, mode="hybrid")


def main() -> None:
    ap = argparse.ArgumentParser()
    ap.add_argument("--set", type=Path, default=DEFAULT_SET)
    ap.add_argument("--split", choices=["dev", "test", "all"], default="test")
    ap.add_argument("--embedder", choices=["bge-m3", "fake"], default="bge-m3")
    ap.add_argument("--qdrant-url", default="http://localhost:6333")
    ap.add_argument("--collection", default="krishi_mitr_kb")
    ap.add_argument("--ingest-memory", action="store_true", help="ingest the corpus into in-memory Qdrant first")
    ap.add_argument("--query", choices=["original", "english"], default="original")
    ap.add_argument("--category-filter", action="store_true")
    ap.add_argument("--ablate", action="store_true")
    ap.add_argument("--rerank", action="store_true", help="include the bge-reranker row in --ablate")
    ap.add_argument("--show-misses", action="store_true")
    ap.add_argument("--out", type=Path, default=None, help="write the JSON report here")
    args = ap.parse_args()

    rows = load_rows(args.set, args.split)
    retriever = build_retriever(args)
    report = {"split": args.split, "embedder": args.embedder, "query": args.query, "category_filter": args.category_filter,
              "collection": args.collection, "main": evaluate(rows, retriever, args.query, args.category_filter)}
    if args.embedder == "fake":
        report["WARNING"] = "FakeEmbedder: plumbing check only, these numbers say nothing about retrieval quality."
    if args.ablate:
        report["ablation"] = ablation(rows, retriever, args.rerank, args.category_filter)
    if not args.show_misses:
        report["main"].pop("misses")
    text = json.dumps(report, ensure_ascii=False, indent=2)
    print(text)
    if args.out:
        args.out.write_text(text + "\n", "utf-8")


if __name__ == "__main__":
    main()
