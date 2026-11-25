"""Qdrant storage: one collection, two named vectors (dense + sparse), payload indexes.

Idempotent ingestion: every point carries `doc_hash`. A document is skipped when the stored hash
equals the file's hash, replaced (delete-by-source_doc then upsert) when it changed, and removed
with --prune when the file is gone. No side manifest, so a recreated collection cannot go stale.
"""
from __future__ import annotations

from typing import Iterable, Optional

from qdrant_client import QdrantClient, models

from app.rag.chunker import Chunk
from app.rag.embedder import Embedded

DENSE, SPARSE = "dense", "sparse"


def connect(url: Optional[str] = None) -> QdrantClient:
    """':memory:' or a directory path = embedded local mode (tests, laptops); http(s)://... = server."""
    url = url or ":memory:"
    if url == ":memory:":
        return QdrantClient(":memory:")
    if url.startswith(("http://", "https://")):
        return QdrantClient(url=url)
    return QdrantClient(path=url)


def ensure_collection(client: QdrantClient, name: str, dense_dim: int) -> None:
    if client.collection_exists(name):
        return
    client.create_collection(
        collection_name=name,
        vectors_config={DENSE: models.VectorParams(size=dense_dim, distance=models.Distance.COSINE)},
        sparse_vectors_config={SPARSE: models.SparseVectorParams()},
    )
    for field in ("category", "crops", "language", "source_doc"):
        client.create_payload_index(name, field_name=field, field_schema=models.PayloadSchemaType.KEYWORD)


def stored_doc_hashes(client: QdrantClient, name: str) -> dict[str, str]:
    """{source_doc: doc_hash} for every document currently in the collection."""
    out: dict[str, str] = {}
    offset = None
    while True:
        pts, offset = client.scroll(name, limit=256, offset=offset, with_payload=["source_doc", "doc_hash"],
                                    with_vectors=False)
        for p in pts:
            out[p.payload["source_doc"]] = p.payload["doc_hash"]
        if offset is None:
            return out


def delete_doc(client: QdrantClient, name: str, source_doc: str) -> None:
    client.delete(name, points_selector=models.FilterSelector(filter=models.Filter(
        must=[models.FieldCondition(key="source_doc", match=models.MatchValue(value=source_doc))])), wait=True)


def upsert_chunks(client: QdrantClient, name: str, chunks: list[Chunk], vecs: list[Embedded]) -> None:
    points = [
        models.PointStruct(
            id=c.point_id,
            vector={DENSE: v.dense, SPARSE: models.SparseVector(indices=v.sparse_indices, values=v.sparse_values)},
            payload={"chunk_id": c.chunk_id, "text": c.text, "source_doc": c.source_doc,
                     "section_title": c.section_title, "category": c.category, "language": c.language,
                     "crops": c.crops, "tokens": c.tokens, "doc_hash": c.doc_hash},
        )
        for c, v in zip(chunks, vecs)
    ]
    client.upsert(name, points=points, wait=True)


def build_filter(category: Optional[str], crop_id: Optional[str]) -> Optional[models.Filter]:
    must = []
    if category:
        must.append(models.FieldCondition(key="category", match=models.MatchValue(value=category)))
    if crop_id:  # crop-specific chunks for this crop OR generic chunks (no crop restriction)
        must.append(models.Filter(should=[
            models.FieldCondition(key="crops", match=models.MatchValue(value=crop_id)),
            models.IsEmptyCondition(is_empty=models.PayloadField(key="crops")),
        ]))
    return models.Filter(must=must) if must else None


def hybrid_query(client: QdrantClient, name: str, emb: Embedded, flt: Optional[models.Filter],
                 limit: int, prefetch_k: int = 20, mode: str = "hybrid"):
    """mode: hybrid (dense + sparse, RRF fusion inside Qdrant) | dense | sparse  (ablations)."""
    sparse_q = models.SparseVector(indices=emb.sparse_indices, values=emb.sparse_values)
    if mode == "dense":
        res = client.query_points(name, query=emb.dense, using=DENSE, query_filter=flt, limit=limit, with_payload=True)
    elif mode == "sparse":
        res = client.query_points(name, query=sparse_q, using=SPARSE, query_filter=flt, limit=limit, with_payload=True)
    else:
        res = client.query_points(
            name,
            prefetch=[
                models.Prefetch(query=emb.dense, using=DENSE, filter=flt, limit=prefetch_k),
                models.Prefetch(query=sparse_q, using=SPARSE, filter=flt, limit=prefetch_k),
            ],
            query=models.FusionQuery(fusion=models.Fusion.RRF), limit=limit, with_payload=True)
    return res.points
