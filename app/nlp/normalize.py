"""Text normalizer. Used at ingestion and on every query, on the ORIGINAL text
before translation (so unit/name hints are read from what the farmer said).

normalize_text : NFKC, Devanagari digits -> ASCII, danda -> '.', strip zero-width
                 chars, collapse whitespace.  Meaning-preserving.
fold           : aggressive spelling fold used ONLY for matching (units, names):
                 lowercase, drop nukta/anusvara/chandrabindu, ऱ->र, long->short
                 vowels. Both query and lexicon entries go through it.
"""
from __future__ import annotations

import re
import unicodedata

_DEVANAGARI_DIGITS = {ord(c): str(i) for i, c in enumerate("०१२३४५६७८९")}
_ZERO_WIDTH = re.compile("[​‌‍⁠﻿]")
_WS = re.compile(r"\s+")
_PUNCT_MAP = str.maketrans(
    {
        "।": ".",
        "॥": ".",
        "“": '"',
        "”": '"',
        "‘": "'",
        "’": "'",
        "–": "-",
        "—": "-",
        "…": "...",
    }
)


def normalize_text(s: str) -> str:
    if not s:
        return ""
    s = unicodedata.normalize("NFKC", s)
    s = _ZERO_WIDTH.sub("", s)
    s = s.translate(_DEVANAGARI_DIGITS)
    s = s.translate(_PUNCT_MAP)
    s = _WS.sub(" ", s).strip()
    return s


_FOLD_MAP = str.maketrans(
    {
        "़": None,  # nukta
        "ं": None,  # anusvara
        "ँ": None,  # chandrabindu
        "ऱ": "र",  # ऱ -> र
        "ऩ": "न",  # ऩ -> न
        "ी": "ि",  # ी -> ि
        "ू": "ु",  # ू -> ु
        "ॉ": "ा",  # ॉ -> ा
        "ॅ": "े",  # ॅ -> े
    }
)


def fold(s: str) -> str:
    s = normalize_text(s).lower()
    return s.translate(_FOLD_MAP)
