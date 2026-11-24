"""Colloquial units → canonical integers. The LLM passes what the farmer said
(`quantity=20, unit="bori"`); tools convert here so "20 bori" is 1000 kg, never 20."""

from __future__ import annotations

import unicodedata
from typing import Literal

# One bori / goni / bag of onion or grain = 50 kg (the platform's convention,
# NLP plan §1 rule 4). Khandi is deliberately absent: it varies by region/crop.
_KG_PER_UNIT: dict[str, int] = {
    "kg": 1, "kgs": 1, "kilo": 1, "kilogram": 1, "किलो": 1, "किग्रा": 1,
    "quintal": 100, "quintals": 100, "qtl": 100, "q": 100, "क्विंटल": 100, "क्विंटल": 100, "कुंटल": 100,
    "bori": 50, "bora": 50, "bag": 50, "bags": 50, "goni": 50, "gooni": 50, "katta": 50,
    "बोरी": 50, "बोरा": 50, "गोणी": 50, "गोणे": 50, "पोते": 50, "पोती": 50, "कट्टा": 50,
    "ton": 1000, "tons": 1000, "tonne": 1000, "tonnes": 1000, "टन": 1000,
}

UnitName = Literal["kg", "quintal", "bori", "goni", "bag", "ton"]


def kg_per(unit: str) -> int:
    key = unicodedata.normalize("NFKC", unit or "kg").strip().lower()
    if key not in _KG_PER_UNIT:
        raise ValueError(f"unknown unit {unit!r}")
    return _KG_PER_UNIT[key]


def to_kg(quantity: float, unit: str = "kg") -> int:
    """Integer kg, rounded to the nearest kg."""
    if quantity is None or quantity <= 0:
        raise ValueError("quantity must be positive")
    return int(round(float(quantity) * kg_per(unit)))


def rupees_to_paise(rupees: float) -> int:
    if rupees is None or rupees <= 0:
        raise ValueError("price must be positive")
    return int(round(float(rupees) * 100))
