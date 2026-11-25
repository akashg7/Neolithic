"""Embedders: BGE-M3 (dense + sparse in one pass) for production, a deterministic fake for tests.

Both return, per text, a dense vector and a sparse vector (indices, values) so the store and
retriever never care which one is running.
"""
from __future__ import annotations

import hashlib
import math
import os
import re
from dataclasses import dataclass
from typing import Protocol

from app.nlp.normalize import fold


@dataclass
class Embedded:
    dense: list[float]
    sparse_indices: list[int]
    sparse_values: list[float]


class Embedder(Protocol):
    dense_dim: int

    def encode(self, texts: list[str]) -> list[Embedded]: ...


class BGEM3Embedder:
    """FlagEmbedding's BGEM3FlagModel: one forward pass gives dense (1024) and sparse weights.

    Needs `pip install FlagEmbedding` and the model download (~2.2 GB). CPU works for the demo
    corpus; use fp16 only on GPU.
    """

    dense_dim = 1024

    def __init__(self, model_name: str = "BAAI/bge-m3", use_fp16: bool = False, batch_size: int = 16):
        from FlagEmbedding import BGEM3FlagModel  # lazy: heavy import

        self._m = BGEM3FlagModel(model_name, use_fp16=use_fp16)
        self._bs = batch_size

    def encode(self, texts: list[str]) -> list[Embedded]:
        out = self._m.encode(texts, batch_size=self._bs, return_dense=True, return_sparse=True,
                             return_colbert_vecs=False, max_length=512)
        res = []
        for dense, lex in zip(out["dense_vecs"], out["lexical_weights"]):
            items = sorted((int(k), float(v)) for k, v in lex.items())
            res.append(Embedded([float(x) for x in dense], [k for k, _ in items], [v for _, v in items]))
        return res


class FakeEmbedder:
    """Hashing embedder for tests / offline dry runs. Lexical overlap => similarity, which is
    enough to test plumbing (hybrid fusion, filters, idempotence). NOT a quality baseline."""

    dense_dim = 128
    _TOK = re.compile(r"[\wऀ-ॿ]+")

    @staticmethod
    def _h(tok: str, mod: int) -> int:
        return int(hashlib.md5(tok.encode()).hexdigest(), 16) % mod

    def encode(self, texts: list[str]) -> list[Embedded]:
        res = []
        for t in texts:
            toks = self._TOK.findall(fold(t))
            dense = [0.0] * self.dense_dim
            sparse: dict[int, float] = {}
            for tok in toks:
                dense[self._h(tok, self.dense_dim)] += 1.0
                sparse[self._h("s" + tok, 50021)] = sparse.get(self._h("s" + tok, 50021), 0.0) + 1.0
            norm = math.sqrt(sum(x * x for x in dense)) or 1.0
            items = sorted(sparse.items())
            res.append(Embedded([x / norm for x in dense], [k for k, _ in items], [v for _, v in items]))
        return res


def make_embedder(name: str | None = None) -> Embedder:
    name = (name or os.getenv("EMBEDDER", "bge-m3")).lower()
    return FakeEmbedder() if name == "fake" else BGEM3Embedder()
