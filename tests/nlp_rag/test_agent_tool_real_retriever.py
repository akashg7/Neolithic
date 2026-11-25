"""Day 4: Person A's `search_agri_knowledge` tool running against Person B's REAL retriever
(in-memory Qdrant + the actual data/rag_corpus, FakeEmbedder so it works offline).

These are wiring tests: filters, crop-id handling, result contract, card/citation shape.
They do not measure retrieval quality (FakeEmbedder is hash-based); that is eval/eval_rag.py with BGE-M3.
"""
import asyncio
import importlib.util
import sys
import warnings
from pathlib import Path

import pytest

from app.agents.tools.base import ToolContext, run_tool
import app.agents.tools.knowledge  # noqa: F401  (registers search_agri_knowledge)
from app.rag import store
from app.rag.chunker import approx_token_counter
from app.rag.embedder import FakeEmbedder
from app.rag.qdrant_retriever import Retriever, set_retriever

warnings.filterwarnings("ignore", message="Payload indexes have no effect")
ROOT = Path(__file__).resolve().parents[2]
CORPUS = ROOT / "data" / "rag_corpus"
CATEGORIES = {"schemes_finance", "grading", "platform", "glossary"}

_spec = importlib.util.spec_from_file_location("ingest_rag", ROOT / "scripts/ingest_rag.py")
_ingest = importlib.util.module_from_spec(_spec)
sys.modules.setdefault("ingest_rag", _ingest)
_spec.loader.exec_module(_ingest)


@pytest.fixture(scope="module")
def retriever():
    emb = FakeEmbedder()
    client = store.connect(":memory:")
    store.ensure_collection(client, "t_kb", emb.dense_dim)
    _ingest.ingest(CORPUS, client, "t_kb", emb, approx_token_counter)
    r = Retriever(client=client, collection="t_kb", embedder=emb, reranker=None)
    set_retriever(r)
    yield r
    set_retriever(None)


@pytest.fixture(autouse=True)
def real_retriever_env(monkeypatch, retriever):
    monkeypatch.setenv("RETRIEVER", "real")


class _Res:
    """run_tool result wrapped so tests read .data / .card / .citation."""
    def __init__(self, out):
        assert out["ok"], out
        self.data, self.card, self.citation = out["data"], out["card"], out["citation"]


def run(**kw):
    ctx = ToolContext(db=None, user=None, locale="en")
    return _Res(asyncio.run(run_tool("search_agri_knowledge", ctx, kw)))


def test_corpus_has_all_four_categories(retriever):
    pts, _ = retriever.client.scroll("t_kb", limit=1000, with_payload=["category"])
    assert {p.payload["category"] for p in pts} == CATEGORIES


@pytest.mark.parametrize("cat", sorted(CATEGORIES))
def test_category_filter_round_trip(cat):
    res = run(query="loan interest grade escrow bori", category=cat)
    assert res.data["count"] > 0
    assert {c["category"] for c in res.data["chunks"]} == {cat}


def test_no_filter_returns_k_chunks_with_contract_fields():
    res = run(query="pledge loan against stored crop")
    assert 0 < res.data["count"] <= 4
    for c in res.data["chunks"]:
        assert {"chunk_id", "text", "source_doc", "section_title", "category", "language", "score"} <= set(c)
    assert res.card["type"] == "RAG_CITATION"
    assert res.citation["chunk_id"] == res.data["chunks"][0]["chunk_id"]


@pytest.mark.parametrize("crop_arg", ["onion", "Onion", "kanda", "कांदा"])
def test_crop_filter_resolves_aliases_and_keeps_generic_chunks(crop_arg, retriever):
    res = run(query="grade standards moisture", crop=crop_arg)
    assert res.data["count"] > 0
    ids = [c["chunk_id"] for c in res.data["chunks"]]
    pts, _ = retriever.client.scroll("t_kb", limit=1000, with_payload=["chunk_id", "crops"])
    crops_by_id = {p.payload["chunk_id"]: p.payload["crops"] for p in pts}
    for i in ids:  # every hit is onion-specific OR crop-agnostic, never another crop's chunk
        assert (not crops_by_id[i]) or "cmd_onion" in crops_by_id[i]


def test_other_crop_chunks_are_excluded(retriever):
    res = run(query="soyabean grade", crop="onion")
    for c in res.data["chunks"]:
        assert c["source_doc"] != "grading/wdra_soyabean_grade_standards.md"


def test_unknown_crop_does_not_crash_and_keeps_generic_chunks():
    res = run(query="how do I register on e-NAM", crop="dragonfruit")
    assert res.data["count"] > 0


def test_category_and_crop_combine():
    res = run(query="grade", category="grading", crop="soyabean")
    assert res.data["count"] > 0
    assert {c["category"] for c in res.data["chunks"]} == {"grading"}
    assert all(c["source_doc"] != "grading/wdra_onion_grade_standards.md" for c in res.data["chunks"])
