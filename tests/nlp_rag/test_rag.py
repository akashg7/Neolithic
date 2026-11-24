import asyncio
import importlib.util
import re
import sys
import warnings
from pathlib import Path

import pytest

from app.contracts import RetrievedChunk
from app.rag import store
from app.rag.chunker import (chunk_document, parse_front_matter, split_sections, window_section, word_counter,
                             TARGET_MAX, TARGET_MIN)
from app.rag.embedder import FakeEmbedder
from app.rag.qdrant_retriever import Retriever

warnings.filterwarnings("ignore", message="Payload indexes have no effect")
ROOT = Path(__file__).resolve().parents[2]
spec = importlib.util.spec_from_file_location("ingest_rag", ROOT / "scripts/ingest_rag.py")
ingest_mod = importlib.util.module_from_spec(spec)
sys.modules["ingest_rag"] = ingest_mod
spec.loader.exec_module(ingest_mod)


def para(n_sent: int, tag: str, words: int = 20) -> str:
    return " ".join(f"{tag} sentence {i} " + "word " * (words - 3) + "." for i in range(n_sent))


# ---------------------------------------------------------------------------- parsing
def test_front_matter():
    meta, body = parse_front_matter("---\ntitle: Onion grades\nlanguage: en\ncrops: [onion, wheat]\n---\n# H\ntext")
    assert meta == {"title": "Onion grades", "language": "en", "crops": ["onion", "wheat"]}
    assert body.startswith("# H")
    assert parse_front_matter("no front matter") == ({}, "no front matter")


def test_sections_track_heading_path_and_ignore_fenced_headings():
    md = "intro\n# A\na text\n## B\nb text\n```\n# not a heading\n```\n## C\nc text\n# D\nd text"
    secs = split_sections(md)
    assert [s.path for s in secs] == [[], ["A"], ["A", "B"], ["A", "C"], ["D"]]
    assert "# not a heading" in secs[2].text


# ---------------------------------------------------------------------------- windows
def test_short_section_stays_whole():
    assert window_section("one two three.", word_counter) == ["one two three."]


def test_long_section_windows_have_size_and_overlap():
    text = para(60, "x")  # ~60 sentences * 20 words = 1200 words
    wins = window_section(text, word_counter)
    assert len(wins) >= 3
    assert all(word_counter(w) <= TARGET_MAX for w in wins)
    assert all(word_counter(w) >= TARGET_MIN for w in wins[:-1])
    # ~15% overlap: consecutive windows share sentences
    for a, b in zip(wins, wins[1:]):
        shared = set(re.findall(r"x sentence \d+", a)) & set(re.findall(r"x sentence \d+", b))
        assert shared, "no overlap between consecutive windows"
        assert word_counter(" ".join(sorted(shared))) <= TARGET_MAX * 0.30
    # nothing lost
    covered = set(re.findall(r"x sentence \d+", " ".join(wins)))
    assert len(covered) == 60


def test_single_huge_sentence_is_split():
    wins = window_section("word " * 1500 + ".", word_counter)
    assert len(wins) >= 3 and all(word_counter(w) <= TARGET_MAX for w in wins)


# ---------------------------------------------------------------------------- documents
DOC = "---\ntitle: Onion grading\nlanguage: en\ncrops: [onion]\n---\n# Onion grading\n## Grade A\n" + para(3, "a") + "\n## Grade B\n" + para(2, "b")


def test_chunk_document_metadata_prefix_and_ids():
    cs = chunk_document("grading/onion.md", DOC, word_counter)
    assert [c.section_title for c in cs] == ["Onion grading > Grade A", "Onion grading > Grade B"]
    c = cs[0]
    assert c.category == "grading" and c.language == "en" and c.crops == ["cmd_onion"]
    assert c.embed_text.startswith("Onion grading | Onion grading > Grade A\n") and c.text in c.embed_text
    assert not c.text.startswith("Onion grading")  # raw text has no prefix
    assert c.chunk_id == "grading/onion.md::onion-grading-grade-a::0"
    assert len({x.point_id for x in cs}) == len(cs)


def test_ids_are_stable_across_runs_and_hash_tracks_content():
    a = chunk_document("grading/onion.md", DOC, word_counter)
    b = chunk_document("grading/onion.md", DOC, word_counter)
    assert [x.chunk_id for x in a] == [x.chunk_id for x in b]
    assert [x.point_id for x in a] == [x.point_id for x in b]
    c = chunk_document("grading/onion.md", DOC + "\nmore", word_counter)
    assert a[0].doc_hash != c[0].doc_hash


def test_devanagari_digits_normalised_and_language_rules():
    cs = chunk_document("glossary/u.md", "---\nlanguage: mr\n---\n# U\n१ बोरी = ५० किलो", word_counter)
    assert cs[0].text == "1 बोरी = 50 किलो" and cs[0].language == "mr"
    assert chunk_document("platform/x.md", "# T\nhello world", word_counter)[0].language == "en"
    assert chunk_document("platform/x.md", "# T\nबोरी hello", word_counter)[0].language == "bilingual"


def test_bad_category_rejected():
    with pytest.raises(ValueError):
        chunk_document("misc/x.md", "# T\nx", word_counter)


def test_duplicate_headings_get_distinct_ids():
    cs = chunk_document("platform/x.md", "# T\n## Same\none\n## Same\ntwo", word_counter)
    assert len({c.chunk_id for c in cs}) == 2


def test_real_glossary_is_in_the_corpus_and_chunks():
    from app.rag.chunker import iter_corpus
    docs = dict(iter_corpus(ROOT / "data/rag_corpus"))
    assert "glossary/units.md" in docs
    cs = chunk_document("glossary/units.md", docs["glossary/units.md"], word_counter)
    bori = next(c for c in cs if "bori" in c.section_title)
    assert "1 bori = 50 kg" in bori.text


# ---------------------------------------------------------------------------- ingest + retrieve (Qdrant local mode)
@pytest.fixture
def corpus(tmp_path):
    def w(rel, text):
        p = tmp_path / rel
        p.parent.mkdir(parents=True, exist_ok=True)
        p.write_text(text, "utf-8")
    w("schemes_finance/kcc.md", "---\ntitle: Kisan Credit Card\nlanguage: en\n---\n# Kisan Credit Card\n## Eligibility\nFarmers who own or lease land can get a Kisan Credit Card loan for crop expenses.\n## Documents\nBring land records and an identity proof to the bank.")
    w("grading/onion.md", "---\ntitle: Onion grading\nlanguage: en\ncrops: [onion]\n---\n# Onion grading\n## Grade A\nGrade A onion has firm bulbs, no sprouting and low moisture.")
    w("grading/wheat.md", "---\ntitle: Wheat grading\nlanguage: en\ncrops: [wheat]\n---\n# Wheat grading\n## Grade A\nGrade A wheat has low moisture and few broken grains.")
    w("platform/listing.md", "---\ntitle: Listing a lot\nlanguage: en\n---\n# Listing a lot\nOpen the Sell tab, enter the commodity and quantity, then tap Confirm.")
    w("glossary/units.md", "---\ntitle: Units\nlanguage: bilingual\n---\n# Units\n## bori\n1 bori = 50 kg. Also called bag, बोरी.")
    return tmp_path


def run_ingest(corpus, client, **kw):
    return ingest_mod.ingest(corpus, client, "t", FakeEmbedder(), word_counter, **kw)


def test_ingest_is_idempotent_and_detects_changes(corpus):
    client = store.connect(":memory:")
    s1 = run_ingest(corpus, client)
    assert s1["added"] == 5 and s1["skipped"] == 0 and s1["chunks"] >= 6
    n = client.count("t").count
    s2 = run_ingest(corpus, client)
    assert s2["skipped"] == 5 and s2["added"] == 0 and s2["updated"] == 0 and client.count("t").count == n
    # edit one file: only that one is re-embedded, old chunks replaced (no duplicates)
    (corpus / "platform/listing.md").write_text("---\ntitle: Listing a lot\nlanguage: en\n---\n# Listing a lot\nNew steps: tap Sell, then Confirm.", "utf-8")
    s3 = run_ingest(corpus, client)
    assert s3["updated"] == 1 and s3["skipped"] == 4 and client.count("t").count == n
    hits = Retriever(client, "t", FakeEmbedder(), reranker=None).search_sync("new steps tap sell")
    assert any("New steps" in h.text for h in hits) and not any("Open the Sell tab" in h.text for h in hits)


def test_prune_and_force(corpus):
    client = store.connect(":memory:")
    run_ingest(corpus, client)
    (corpus / "grading/wheat.md").unlink()
    assert run_ingest(corpus, client)["removed"] == 0           # not pruned unless asked
    assert run_ingest(corpus, client, prune=True)["removed"] == 1
    assert "grading/wheat.md" not in store.stored_doc_hashes(client, "t")
    assert run_ingest(corpus, client, force=True)["updated"] == 4


@pytest.fixture
def retriever(corpus):
    client = store.connect(":memory:")
    run_ingest(corpus, client)
    return Retriever(client, "t", FakeEmbedder(), reranker=None)


def test_retrieval_returns_contract_type_and_relevant_chunk(retriever):
    hits = retriever.search_sync("how many kg is one bori", "en", k=4)
    assert hits and all(isinstance(h, RetrievedChunk) for h in hits)
    assert hits[0].chunk_id.startswith("glossary/units.md") and "50 kg" in hits[0].text
    assert hits[0].category == "glossary" and hits[0].score > 0


def test_category_filter(retriever):
    hits = retriever.search_sync("grade A moisture", category="grading", k=4)
    assert hits and {h.category for h in hits} == {"grading"}


def test_crop_filter_keeps_matching_and_generic_chunks_only(retriever):
    hits = retriever.search_sync("grade A low moisture", crop="onion", k=10)
    docs = {h.source_doc for h in hits}
    assert "grading/onion.md" in docs and "grading/wheat.md" not in docs
    assert "platform/listing.md" in docs or "glossary/units.md" in docs  # generic docs are not excluded
    hits_hi = retriever.search_sync("grade A low moisture", crop="कांदा", k=10)  # Marathi crop name resolves
    assert "grading/wheat.md" not in {h.source_doc for h in hits_hi}


def test_modes_for_ablation_all_work(retriever, corpus):
    for mode in ("hybrid", "dense", "sparse"):
        r = Retriever(retriever.client, "t", FakeEmbedder(), reranker=None, mode=mode)
        assert r.search_sync("kisan credit card eligibility", k=2)[0].source_doc == "schemes_finance/kcc.md"


def test_empty_query_and_k(retriever):
    assert retriever.search_sync("   ") == []
    assert len(retriever.search_sync("onion", k=2)) == 2


def test_reranker_reorders_and_is_timed(retriever):
    class Rev:  # prefers the LAST candidate
        def compute_score(self, pairs, normalize=True):
            return [float(i) for i in range(len(pairs))]
    plain = retriever.search_sync("grade A", k=3)
    r = Retriever(retriever.client, "t", FakeEmbedder(), reranker=Rev())
    out = r.search_sync("grade A", k=3)
    assert [h.chunk_id for h in out] != [h.chunk_id for h in plain]
    assert r.rerank_median_ms() is not None


def test_async_search_and_module_switch(retriever, monkeypatch):
    from app.rag import qdrant_retriever, retriever as facade
    qdrant_retriever.set_retriever(retriever)
    monkeypatch.setenv("RETRIEVER", "real")
    try:
        hits = asyncio.run(facade.search("listing a lot: sell tab, confirm", "en"))
        assert hits[0].source_doc == "platform/listing.md"
        monkeypatch.setenv("RETRIEVER", "stub")
        assert asyncio.run(facade.search("anything", "en"))[0].chunk_id.startswith("stub_")  # Day-1 stub still works
    finally:
        qdrant_retriever.set_retriever(None)


def test_stub_retriever_respects_category_and_k():
    from app.rag import retriever as facade
    out = asyncio.run(facade.search("x", "en", category="grading", k=4))
    assert [c.category for c in out] == ["grading"]
