"""Unit parser: number + unit in mr / hi / en  ->  kilograms.

    to_kg(20, "bori")                 -> 1000
    parse_quantities("२० बोरी कांदा")  -> [Quantity(value=20, unit='bori', kg=1000)]

Unit sizes live in data/units.json (generated into the glossary corpus by
scripts/build_glossary.py). Units whose size varies by region (khandi, goni,
maund) have kg=null: to_kg raises UnknownUnitError and the agent asks the
farmer. It never guesses.
"""
from __future__ import annotations

import json
import math
import re
from dataclasses import dataclass
from pathlib import Path
from typing import Optional

from app.nlp.normalize import fold

_DATA = json.loads((Path(__file__).parent / "data" / "units.json").read_text("utf-8"))


class UnknownUnitError(ValueError):
    """Unit not recognised, or its size is not fixed (ask the farmer)."""

    def __init__(self, unit: str, reason: str = "unknown"):
        super().__init__(f"{reason} unit: {unit!r}")
        self.unit = unit
        self.reason = reason  # "unknown" | "variable_size"


# --- lookup tables (all keys folded) ------------------------------------------
_UNIT_BY_ALIAS: dict[str, str] = {}
_KG_BY_UNIT: dict[str, Optional[float]] = {}
for _canon, _spec in _DATA["units"].items():
    _KG_BY_UNIT[_canon] = _spec["kg"]
    for _a in [_canon, *_spec["aliases"]]:
        _UNIT_BY_ALIAS[fold(_a)] = _canon

_NUM: dict[str, float] = {}
for _v, _words in _DATA["number_words"].items():
    for _w in _words:
        _NUM[fold(_w)] = float(_v)
_MULT: dict[str, float] = {
    fold(w): float(v) for v, ws in _DATA["multipliers"].items() for w in ws
}
_FRAC: dict[str, float] = {
    fold(w): float(v) for v, ws in _DATA["fractions"].items() for w in ws
}
_SADE: set[str] = {fold(w) for w in _DATA["sade_prefix"]}

# Marathi / Hindi case suffixes that may follow a unit (क्विंटलचा, किलोमध्ये ...)
_UNIT_SUFFIXES = ("च्या", "चा", "ची", "चे", "चं", "ला", "ने", "मध्ये", "में", "का", "की", "के", "भर", "ंचा")


def _alt(words) -> str:
    return "|".join(re.escape(w) for w in sorted(set(words), key=len, reverse=True))


_LEFT = r"(?<![\wऀ-ॿ])"
_RIGHT = r"(?![\wऀ-ॿ])"
_WORD_TOKENS = _alt([*_NUM, *_MULT, *_FRAC])
_SADE_RE = _alt(_SADE)
_DIGITS = r"\d{1,3}(?:,\d{3})+(?:\.\d+)?|\d+(?:\.\d+)?"
_NUMBER = (
    rf"(?:(?P<digits>{_DIGITS})(?:\s*(?P<dmult>{_alt(_MULT)}){_RIGHT})?"
    rf"|(?P<words>(?:(?:{_SADE_RE})\s*)?(?:{_WORD_TOKENS})(?:\s+(?:{_WORD_TOKENS}))*))"
)
_UNIT = rf"(?P<unit>{_alt(_UNIT_BY_ALIAS)})(?:{_alt(fold(s) for s in _UNIT_SUFFIXES)})?{_RIGHT}"
_QTY_RE = re.compile(rf"{_LEFT}{_NUMBER}\s*{_UNIT}")


@dataclass(frozen=True)
class Quantity:
    value: float
    unit: str  # canonical: kg | quintal | ton | bori | khandi | goni | maund
    kg: Optional[int]  # None when the unit's size is not fixed
    raw: str


def _words_to_value(phrase: str) -> float:
    tokens: list[str] = []
    for t in phrase.split():
        if t in _SADE:
            tokens.append(t)
            continue
        glued = next((s for s in _SADE if t.startswith(s) and len(t) > len(s)), None)
        if glued and t[len(glued):] in _NUM:
            tokens += [glued, t[len(glued):]]
        else:
            tokens.append(t)
    total = 0.0
    cur: Optional[float] = None
    sade = False
    for t in tokens:
        if t in _SADE:
            sade = True
        elif t in _FRAC:
            cur = (cur or 0.0) + _FRAC[t]
        elif t in _NUM:
            cur = (cur or 0.0) + _NUM[t]
        elif t in _MULT:
            m = _MULT[t]
            cur = (1.0 if cur is None else cur) * m
            if m >= 1000:
                total += cur
                cur = None
    value = total + (cur or 0.0)
    return value + 0.5 if sade else value


def _round_half_up(x: float) -> int:
    return int(math.floor(x + 0.5))


def canonical_unit(unit: str) -> str:
    canon = _UNIT_BY_ALIAS.get(fold(unit))
    if canon is None:
        raise UnknownUnitError(unit, "unknown")
    return canon


def to_kg(value: float, unit: str) -> int:
    """Convert a quantity to whole kilograms. Raises UnknownUnitError."""
    if value is None or value <= 0:
        raise ValueError(f"quantity must be positive, got {value!r}")
    canon = canonical_unit(unit)
    factor = _KG_BY_UNIT[canon]
    if factor is None:
        raise UnknownUnitError(unit, "variable_size")
    return _round_half_up(value * factor)


def parse_quantities(text: str) -> list[Quantity]:
    """Find every 'number + unit' in the text (original language, any script)."""
    out: list[Quantity] = []
    for m in _QTY_RE.finditer(fold(text)):
        if m.group("digits") is not None:
            value = float(m.group("digits").replace(",", ""))
            if m.group("dmult"):
                value *= _MULT[m.group("dmult")]
        else:
            value = _words_to_value(m.group("words"))
        if value <= 0:
            continue
        canon = _UNIT_BY_ALIAS[m.group("unit")]
        factor = _KG_BY_UNIT[canon]
        kg = None if factor is None else _round_half_up(value * factor)
        out.append(Quantity(value=value, unit=canon, kg=kg, raw=m.group(0)))
    return out
