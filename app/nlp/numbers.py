"""Number extraction shared by the translation round-trip tests and Person A's
number-check guard.

extract_numbers("२० बोरी at ₹1,800 and 12.5%") -> [20.0, 1800.0, 12.5]
numbers_preserved(english_reply, translated_reply) -> True if every number in
the English reply also appears in the translated reply (Devanagari digits
converted first).
"""
from __future__ import annotations

import re
from collections import Counter

from app.nlp.normalize import normalize_text

_NUM_RE = re.compile(r"(?<![\w.])\d{1,3}(?:,\d{3})+(?:\.\d+)?|(?<![\w.])\d+(?:\.\d+)?")


def extract_numbers(text: str) -> list[float]:
    out = []
    for m in _NUM_RE.findall(normalize_text(text)):
        out.append(float(m.replace(",", "")))
    return out


def numbers_preserved(source: str, translated: str) -> bool:
    """Every number in `source` is present (same multiplicity) in `translated`."""
    need = Counter(extract_numbers(source))
    have = Counter(extract_numbers(translated))
    return all(have[n] >= c for n, c in need.items())
