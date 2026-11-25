"""Day 0 frozen contracts shared by Person A (agent) and Person B (NLP/RAG/eval).

Change anything here only after both people agree. Everything else in the repo
imports these types instead of redefining them.
"""
from __future__ import annotations

from enum import Enum
from typing import Any, Optional

from pydantic import BaseModel, Field


# --- 4. Intent labels (frozen) -------------------------------------------------
class Intent(str, Enum):
    PRICE = "PRICE"
    WINDOW = "WINDOW"
    LOT = "LOT"
    GRADE = "GRADE"
    PORTFOLIO = "PORTFOLIO"
    RAG = "RAG"
    ONBOARD = "ONBOARD"
    NAVIGATE = "NAVIGATE"
    SMALLTALK = "SMALLTALK"
    OUT_OF_SCOPE = "OUT_OF_SCOPE"


INTENT_LABELS: list[str] = [i.value for i in Intent]


# --- 3. Tool result envelope ---------------------------------------------------
class ToolResult(BaseModel):
    """Every agent tool returns this shape; response builder and evals read it."""

    ok: bool
    data: dict[str, Any] = Field(default_factory=dict)
    source: str = ""
    card: Optional[dict[str, Any]] = None
    error: Optional[str] = None


# --- 1. Retriever --------------------------------------------------------------
class RetrievedChunk(BaseModel):
    chunk_id: str
    text: str
    source_doc: str
    section_title: str
    category: str  # schemes_finance | grading | platform | glossary
    language: str  # en | mr | hi | bilingual
    score: float


RAG_CATEGORIES = ("schemes_finance", "grading", "platform", "glossary")


# --- 6. Translation layer ------------------------------------------------------
class Translated(BaseModel):
    original: str  # transcript or typed text, as the farmer gave it
    english: str
    source_lang: str  # mr | hi | en
    # {'quantity_kg': 1000, 'commodity': 'cmd_onion', 'mandi': 'mkt_lasalgaon'}
    hints: dict[str, Any] = Field(default_factory=dict)


# --- 5. Eval row (one JSON object per line, shared by every eval script) -------
class EvalRow(BaseModel):
    id: str
    split: str  # dev | test
    locale: str  # mr | hi | en
    turns_original: list[str]
    turns_english: list[str]
    screen_context: dict[str, Any] = Field(default_factory=dict)
    expected_intent: str
    expected_tool: Optional[str] = None
    expected_args: dict[str, Any] = Field(default_factory=dict)
    expected_chunk_ids: list[str] = Field(default_factory=list)
    must_refuse: bool = False
