"""Retriever interface (Person B provides, Person A calls).

Day 1: STUB returning fixed chunks so Person A's search_agri_knowledge tool can be
built. Day 3: replaced by the real hybrid retriever in app/rag/qdrant_retriever.py
(selected with RETRIEVER=real).
"""
from __future__ import annotations

import logging
import os
from typing import Optional

from app.contracts import RetrievedChunk

log = logging.getLogger("krishi.retriever.facade")

_STUB_CHUNKS = [
    RetrievedChunk(
        chunk_id="stub_schemes_001",
        text="Kisan Credit Card (KCC) gives farmers short-term credit for crop "
        "inputs at a subsidised interest rate. Apply at your bank with land records.",
        source_doc="schemes_finance/kcc.md",
        section_title="Kisan Credit Card > Eligibility",
        category="schemes_finance",
        language="en",
        score=0.91,
    ),
    RetrievedChunk(
        chunk_id="stub_grading_001",
        text="Grade A onion: size 55 mm and above, moisture below 10 percent, "
        "no sprouting, firm bulbs.",
        source_doc="grading/onion_grades.md",
        section_title="Onion grades > Grade A",
        category="grading",
        language="en",
        score=0.84,
    ),
    RetrievedChunk(
        chunk_id="stub_platform_001",
        text="To list a lot, open the Sell tab, enter commodity, quantity and "
        "expected price, then tap Confirm.",
        source_doc="platform/how_to_list.md",
        section_title="Listing a lot",
        category="platform",
        language="en",
        score=0.80,
    ),
    RetrievedChunk(
        chunk_id="stub_glossary_001",
        text="1 bori (bag) of onion is about 50 kg. 1 quintal is 100 kg.",
        source_doc="glossary/units.md",
        section_title="Units > bori",
        category="glossary",
        language="en",
        score=0.77,
    ),
]


async def _stub_search(query, locale, category, crop, k):
    pool = [c for c in _STUB_CHUNKS if category is None or c.category == category]
    return pool[:k]


async def search(
    query: str,
    locale: str,
    category: Optional[str] = None,
    crop: Optional[str] = None,
    k: int = 4,
) -> list[RetrievedChunk]:
    if os.getenv("RETRIEVER", "stub") == "real":
        try:
            from app.rag.qdrant_retriever import search as real_search

            hits = await real_search(query, locale, category, crop, k)
            if hits:
                return hits
        except Exception as exc:
            log.warning("Real Qdrant retriever failed (%s); falling back to stub chunks", exc)
    return await _stub_search(query, locale, category, crop, k)
