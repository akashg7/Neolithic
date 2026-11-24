"""Chunk the corpus, embed it (BGE-M3 dense + sparse) and load it into Qdrant. Idempotent.

    python scripts/ingest_rag.py                              # real: Qdrant at $QDRANT_URL, BGE-M3
    python scripts/ingest_rag.py --dry-run                    # chunk stats only, no models, no Qdrant
    python scripts/ingest_rag.py --qdrant-url :memory: --embedder fake   # plumbing check

Unchanged files (same sha256) are skipped; changed files are replaced; --prune removes files that no
longer exist; --force re-embeds everything.
"""
from __future__ import annotations

import argparse
import os
import statistics
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))

from app.rag import store  # noqa: E402
from app.rag.chunker import approx_token_counter, bge_m3_token_counter, chunk_document, iter_corpus, TARGET_MAX  # noqa: E402
from app.rag.embedder import make_embedder  # noqa: E402


def ingest(corpus: Path, client, collection: str, embedder, count, force=False, prune=False) -> dict:
    docs = iter_corpus(corpus)
    store.ensure_collection(client, collection, embedder.dense_dim)
    have = store.stored_doc_hashes(client, collection)
    stats = {"added": 0, "updated": 0, "skipped": 0, "removed": 0, "chunks": 0}
    for rel, raw in docs:
        chunks = chunk_document(rel, raw, count)
        if not chunks:
            continue
        doc_hash = chunks[0].doc_hash
        if not force and have.get(rel) == doc_hash:
            stats["skipped"] += 1
            continue
        if rel in have:
            store.delete_doc(client, collection, rel)
            stats["updated"] += 1
        else:
            stats["added"] += 1
        vecs = []
        for i in range(0, len(chunks), 32):
            vecs += embedder.encode([c.embed_text for c in chunks[i:i + 32]])
        store.upsert_chunks(client, collection, chunks, vecs)
        stats["chunks"] += len(chunks)
    if prune:
        present = {rel for rel, _ in docs}
        for gone in set(have) - present:
            store.delete_doc(client, collection, gone)
            stats["removed"] += 1
    return stats


def dry_run(corpus: Path, count) -> None:
    allc = []
    for rel, raw in iter_corpus(corpus):
        allc += chunk_document(rel, raw, count)
    if not allc:
        print("no documents found under", corpus)
        return
    by_cat: dict[str, int] = {}
    for c in allc:
        by_cat[c.category] = by_cat.get(c.category, 0) + 1
    toks = [c.tokens for c in allc]
    print(f"{len(allc)} chunks from {len({c.source_doc for c in allc})} docs: {by_cat}")
    print(f"tokens/chunk: min {min(toks)} median {int(statistics.median(toks))} max {max(toks)}")
    over = [c.chunk_id for c in allc if c.tokens > TARGET_MAX * 1.15]
    if over:
        print("WARNING over-long chunks:", over[:5])
    for cat in ("schemes_finance", "grading", "platform", "glossary"):
        if cat not in by_cat:
            print(f"WARNING empty category: {cat}")


def main() -> None:
    ap = argparse.ArgumentParser()
    ap.add_argument("--corpus", default=str(ROOT / "data/rag_corpus"))
    ap.add_argument("--qdrant-url", default=os.getenv("QDRANT_URL", "http://localhost:6333"))
    ap.add_argument("--collection", default=os.getenv("QDRANT_COLLECTION", "krishi_rag"))
    ap.add_argument("--embedder", default=os.getenv("EMBEDDER", "bge-m3"), choices=["bge-m3", "fake"])
    ap.add_argument("--force", action="store_true")
    ap.add_argument("--prune", action="store_true")
    ap.add_argument("--dry-run", action="store_true")
    a = ap.parse_args()
    corpus = Path(a.corpus)
    if a.dry_run:
        dry_run(corpus, approx_token_counter if a.embedder == "fake" else bge_m3_token_counter())
        return
    count = approx_token_counter if a.embedder == "fake" else bge_m3_token_counter()
    stats = ingest(corpus, store.connect(a.qdrant_url), a.collection, make_embedder(a.embedder), count, a.force, a.prune)
    print(stats)


if __name__ == "__main__":
    main()
