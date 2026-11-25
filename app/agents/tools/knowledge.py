"""RAG knowledge search tool wrapping Person B's `app.rag.retriever.search`."""
from __future__ import annotations

from typing import Literal, Optional

from pydantic import BaseModel, Field

from app.agents.tools.base import ToolContext, ToolResult, tool
from app.nlp.lexicon import resolve_commodity
from app.rag.retriever import search as rag_search


class KnowledgeArgs(BaseModel):
    query: str = Field(..., min_length=2, description="English search query for schemes, grading, platform help, or glossary.")
    category: Optional[Literal["schemes_finance", "grading", "platform", "glossary"]] = Field(
        None, description="Optional corpus category filter."
    )
    crop: Optional[str] = Field(None, description="Optional crop filter (e.g. 'onion', 'soyabean').")


@tool(
    "search_agri_knowledge",
    "Search verified agricultural knowledge: government schemes (KCC, WDRA pledge loan, PMFBY, e-NAM), "
    "AGMARK grading standards, post-harvest storage, platform escrow/pooling rules, and unit glossaries.",
    KnowledgeArgs,
)
async def search_agri_knowledge(ctx: ToolContext, args: KnowledgeArgs) -> ToolResult:
    crop_filter = None
    if args.crop:
        resolved = resolve_commodity(args.crop)
        crop_filter = resolved.replace("cmd_", "") if resolved else args.crop.strip().lower()

    chunks = await rag_search(
        query=args.query,
        locale="en",
        category=args.category,
        crop=crop_filter,
        k=4,
    )
    chunk_dicts = [c.model_dump() for c in chunks]
    card = (
        {
            "type": "RAG_CITATION",
            "data": {
                "query": args.query,
                "chunks": [
                    {
                        "chunk_id": c.chunk_id,
                        "source_doc": c.source_doc,
                        "section_title": c.section_title,
                        "category": c.category,
                        "score": round(float(c.score), 3),
                        "snippet": c.text[:240],
                    }
                    for c in chunks
                ],
            },
        }
        if chunks
        else None
    )
    citation = (
        {
            "source": chunks[0].source_doc,
            "title": chunks[0].section_title,
            "chunk_id": chunks[0].chunk_id,
            "section_title": chunks[0].section_title,
        }
        if chunks
        else None
    )
    return ToolResult(
        data={"query": args.query, "count": len(chunk_dicts), "chunks": chunk_dicts},
        card=card,
        citation=citation,
    )
