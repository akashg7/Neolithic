import importlib.util
import json
import sys
from pathlib import Path
from types import SimpleNamespace

import pytest

from app.contracts import EvalRow, RetrievedChunk
from app.rag.chunker import approx_token_counter, chunk_document, iter_corpus

ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(ROOT))
from eval import eval_rag  # noqa: E402

_spec = importlib.util.spec_from_file_location("gen_rag_bench", ROOT / "scripts/gen_rag_bench.py")
gen = importlib.util.module_from_spec(_spec)
_spec.loader.exec_module(gen)

ROWS = eval_rag.load_rows(ROOT / "eval/data/rag_bench.jsonl", "all")


# ----------------------------------------------------------------------------- the dataset
def test_committed_set_matches_generator():
    assert [r.model_dump() for r in gen.build()] == [r.model_dump() for r in ROWS]


def test_every_expected_chunk_id_exists_in_the_corpus():
    ids = {c.chunk_id for rel, raw in iter_corpus(ROOT / "data/rag_corpus")
           for c in chunk_document(rel, raw, approx_token_counter)}
    for r in ROWS:
        assert set(r.expected_chunk_ids) <= ids, r.id


def test_shape_size_and_balance():
    assert len(ROWS) >= 60
    assert len({r.id for r in ROWS}) == len(ROWS)
    for loc in ("mr", "hi", "en"):
        assert sum(r.locale == loc for r in ROWS) >= 20
    dev = [r for r in ROWS if r.split == "dev"]
    test = [r for r in ROWS if r.split == "test"]
    assert dev and test and not ({r.id for r in dev} & {r.id for r in test})
    assert len(test) > len(dev)


def test_answerable_rows_have_chunks_and_refusal_rows_have_none():
    for r in ROWS:
        assert bool(r.expected_chunk_ids) != r.must_refuse, r.id
        assert r.expected_intent == "RAG" and r.expected_tool == "search_agri_knowledge"
        assert r.turns_original and r.turns_english


def test_all_four_categories_are_covered():
    cats = {r.expected_args.get("category") for r in ROWS if not r.must_refuse}
    assert cats == {"schemes_finance", "grading", "platform", "glossary"}


def test_indic_rows_are_really_in_devanagari():
    for r in ROWS:
        if r.locale in ("mr", "hi"):
            assert any("ऀ" <= ch <= "ॿ" for ch in r.turns_original[0]), r.id


# ----------------------------------------------------------------------------- metric math
def test_score_row_hit_recall_mrr():
    s = eval_rag.score_row(["a", "b"], ["x", "a", "y", "z", "w", "b"])  # b is rank 6: outside top 5
    assert s == {"hit": 1.0, "recall": 0.5, "rr": 0.5}


def test_score_row_miss_and_mrr_window():
    assert eval_rag.score_row(["a"], ["x", "y"]) == {"hit": 0.0, "recall": 0.0, "rr": 0.0}
    s = eval_rag.score_row(["a"], ["x"] * 7 + ["a"])  # rank 8: not in top 5, but inside the MRR@10 window
    assert s["hit"] == 0.0 and s["rr"] == pytest.approx(1 / 8)
    assert eval_rag.score_row(["a"], ["x"] * 10 + ["a"])["rr"] == 0.0


def test_aggregate_and_empty():
    agg = eval_rag.aggregate([{"hit": 1, "recall": 1, "rr": 1}, {"hit": 0, "recall": 0, "rr": 0.0}])
    assert agg == {"n": 2, "hit@5": 0.5, "recall@5": 0.5, "mrr@10": 0.5}
    assert eval_rag.aggregate([])["n"] == 0


class _Oracle:
    """Returns the expected chunks first for answerable rows; a junk chunk for everything else."""
    mode, reranker = "hybrid", None

    def __init__(self, rows):
        self.by_text = {r.turns_original[0]: r for r in rows} | {r.turns_english[0]: r for r in rows}
        self.seen_categories = []

    def search_sync(self, text, locale="en", category=None, crop=None, k=4):
        self.seen_categories.append(category)
        r = self.by_text[text]
        ids = list(r.expected_chunk_ids) or ["junk"]
        return [RetrievedChunk(chunk_id=i, text="t", source_doc="d", section_title="s", category="platform",
                               language="en", score=0.9 - 0.01 * n) for n, i in enumerate(ids)][:k]


def test_evaluate_with_oracle_is_perfect_and_separates_refusal_rows():
    rows = [r for r in ROWS if r.split == "test"]
    res = eval_rag.evaluate(rows, _Oracle(rows))
    assert res["overall"]["hit@5"] == res["overall"]["recall@5"] == res["overall"]["mrr@10"] == 1.0
    assert res["overall"]["n"] == sum(not r.must_refuse for r in rows)
    assert res["refusal_rows"]["n"] == sum(r.must_refuse for r in rows)
    assert set(res["by_locale"]) <= {"mr", "hi", "en"} and not res["misses"]


def test_evaluate_reports_misses_and_category_filter_flag():
    rows = [r for r in ROWS if not r.must_refuse][:5]

    class Blind(_Oracle):
        def search_sync(self, text, locale="en", category=None, crop=None, k=4):
            self.seen_categories.append(category)
            return [RetrievedChunk(chunk_id="nope", text="t", source_doc="d", section_title="s",
                                   category="platform", language="en", score=0.1)]

    blind = Blind(rows)
    res = eval_rag.evaluate(rows, blind, use_category=True)
    assert res["overall"]["hit@5"] == 0.0 and len(res["misses"]) == 5
    assert all(c is not None for c in blind.seen_categories)
    plain = Blind(rows)
    eval_rag.evaluate(rows, plain, use_category=False)
    assert set(plain.seen_categories) == {None}


def test_english_query_flag_uses_translated_turn():
    rows = [r for r in ROWS if r.locale == "mr" and not r.must_refuse][:3]
    seen = []

    class Spy(_Oracle):
        def search_sync(self, text, **kw):
            seen.append(text)
            return super().search_sync(text, **kw)

    eval_rag.evaluate(rows, Spy(rows), query="english")
    assert seen == [r.turns_english[0] for r in rows]


# ----------------------------------------------------------------------------- end to end (offline)
def test_end_to_end_runs_offline_with_fake_embedder_including_ablation():
    args = SimpleNamespace(embedder="fake", ingest_memory=True, collection="t_eval", qdrant_url=":memory:")
    retriever = eval_rag.build_retriever(args)
    rows = [r for r in ROWS if r.split == "dev"]
    out = eval_rag.ablation(rows, retriever, with_rerank=False, use_category=False)
    assert set(out) == {f"{m}/{q}" for m in ("dense", "sparse", "hybrid") for q in ("original", "english")}
    for v in out.values():
        assert 0.0 <= v["hit@5"] <= 1.0 and v["n"] > 0
    assert retriever.mode == "hybrid"  # ablation restores the retriever's settings
