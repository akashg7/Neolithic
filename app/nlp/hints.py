"""Hints read from the ORIGINAL farmer text, before translation.

The agent receives the English text plus these hints. If a hint and the model's
tool argument disagree, the hint wins (it was read from the farmer's own words,
so translation cannot mangle 'बोरी' or a mandi name).

Keys (all optional):
  quantity_kg        int   - only when exactly one distinct quantity with a known size
  commodity          str   - only when exactly one commodity ID was found
  mandi              str   - only when exactly one mandi ID was found
  unit_unknown       str   - a unit with no fixed size (khandi, goni): agent must ask
  quantities         list  - every quantity found, when there is more than one
  commodity_candidates / mandi_candidates  list - when several were found
"""
from __future__ import annotations

from typing import Any

from app.nlp.lexicon import scan_names
from app.nlp.normalize import normalize_text
from app.nlp.units import parse_quantities


def extract_hints(original: str) -> dict[str, Any]:
    text = normalize_text(original)
    hints: dict[str, Any] = {}

    quantities = parse_quantities(text)
    known = [q for q in quantities if q.kg is not None]
    unknown = [q for q in quantities if q.kg is None]
    if unknown:
        hints["unit_unknown"] = unknown[0].unit
    if len({q.kg for q in known}) == 1:
        hints["quantity_kg"] = known[0].kg
    elif len(known) > 1:
        hints["quantities"] = [{"value": q.value, "unit": q.unit, "kg": q.kg} for q in known]

    matches = scan_names(text)
    for kind in ("commodity", "mandi"):
        ids = sorted({m.id for m in matches if m.kind == kind})
        if len(ids) == 1:
            hints[kind] = ids[0]
        elif len(ids) > 1:
            hints[f"{kind}_candidates"] = ids
    return hints
