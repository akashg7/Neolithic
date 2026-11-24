"""Real retriever (replaces the Day-1 stub on Day 3; enable with RETRIEVER=real).

query -> normalise -> BGE-M3 dense+sparse -> Qdrant hybrid (RRF inside Qdrant, top 10)
      -> optional bge-reranker-v2-m3 (keep top k) -> RetrievedChunk list.

No HyDE / query rewriting on the live path: the agent's model already writes the search query in its
tool call. `locale` is accepted (evals compare original-language vs translated queries) but BGE-M3 is
multilingual, so it is not used to filter.

Env: QDRANT_URL (":memory:" | path | http://...), QDRANT_COLLECTION (krishi_mitr_kb), EMBEDDER (bge-m3|fake),
     RERANK (on|off, default off until measured), RERANK_MODEL (BAAI/bge-reranker-v2-m3),
     RETRIEVE_MODE (hybrid|dense|sparse) for ablations.
"""
from __future__ import annotations

import asyncio
import logging
import os
import statistics
import time
from typing import Optional

from app.contracts import RetrievedChunk
from app.nlp.lexicon import resolve_commodity
from app.nlp.normalize import normalize_text
from app.rag import store
from app.rag.embedder import Embedder, make_embedder

log = logging.getLogger("krishi.retriever")
CANDIDATES = 10  # fed to the reranker, then cut to k


class Retriever:
    def __init__(self, client=None, collection: Optional[str] = None, embedder: Optional[Embedder] = None,
                 reranker=None, mode: Optional[str] = None):
        self.client = client or store.connect(os.getenv("QDRANT_URL", "http://localhost:6333"))
        self.collection = collection or os.getenv("QDRANT_COLLECTION", "krishi_mitr_kb")
        self.embedder = embedder or make_embedder()
        self.reranker = reranker if reranker is not None else self._load_reranker()
        self.mode = mode or os.getenv("RETRIEVE_MODE", "hybrid")
        self.rerank_ms: list[float] = []

    @staticmethod
    def _load_reranker():
        if os.getenv("RERANK", "off").lower() != "on":
            return None
        from FlagEmbedding import FlagReranker  # lazy

        return FlagReranker(os.getenv("RERANK_MODEL", "BAAI/bge-reranker-v2-m3"), use_fp16=False)

    def search_sync(self, query: str, locale: str = "en", category: Optional[str] = None,
                    crop: Optional[str] = None, k: int = 4) -> list[RetrievedChunk]:
        q = normalize_text(query)
        if not q:
            return []
        crop_id = (resolve_commodity(crop) or crop.lower()) if crop else None
        emb = self.embedder.encode([q])[0]
        flt = store.build_filter(category, crop_id)
        pts = store.hybrid_query(self.client, self.collection, emb, flt, limit=CANDIDATES, mode=self.mode)
        scores = [float(p.score) for p in pts]
        if self.reranker is not None and len(pts) > 1:
            t0 = time.perf_counter()
            scores = [float(s) for s in self.reranker.compute_score([[q, p.payload["text"]] for p in pts], normalize=True)]
            self.rerank_ms.append((time.perf_counter() - t0) * 1000)
            order = sorted(range(len(pts)), key=lambda i: -scores[i])
            pts, scores = [pts[i] for i in order], [scores[i] for i in order]
        return [
            RetrievedChunk(chunk_id=p.payload["chunk_id"], text=p.payload["text"], source_doc=p.payload["source_doc"],
                           section_title=p.payload["section_title"], category=p.payload["category"],
                           language=p.payload["language"], score=s)
            for p, s in list(zip(pts, scores))[:k]
        ]

    async def search(self, *args, **kwargs) -> list[RetrievedChunk]:
        return await asyncio.to_thread(self.search_sync, *args, **kwargs)  # embedding is CPU-bound

    def rerank_median_ms(self) -> Optional[float]:
        return statistics.median(self.rerank_ms) if self.rerank_ms else None


_singleton: Optional[Retriever] = None


def get_retriever() -> Retriever:
    global _singleton
    if _singleton is None:
        _singleton = Retriever()
    return _singleton


def set_retriever(r: Optional[Retriever]) -> None:
    global _singleton
    _singleton = r


async def search(query: str, locale: str, category: Optional[str] = None, crop: Optional[str] = None,
                 k: int = 4) -> list[RetrievedChunk]:
    return await get_retriever().search(query, locale, category, crop, k)
