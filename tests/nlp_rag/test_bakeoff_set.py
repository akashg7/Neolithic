"""The authored bake-off set doubles as a regression test for the hint extractors:
for every prompt, hints read from the ORIGINAL text must agree with expected_args."""
import json
from pathlib import Path

import pytest

from app.contracts import INTENT_LABELS, EvalRow
from app.nlp.hints import extract_hints

PATH = Path(__file__).resolve().parents[2] / "eval/data/bakeoff_40.jsonl"
ROWS = [EvalRow(**json.loads(line)) for line in PATH.read_text("utf-8").splitlines()]


def test_set_shape():
    assert len(ROWS) == 40
    assert len({r.id for r in ROWS}) == 40
    assert {r.locale for r in ROWS} == {"mr", "hi"}
    assert all(r.expected_intent in INTENT_LABELS for r in ROWS)
    assert {r.expected_intent for r in ROWS} == set(INTENT_LABELS) - {"ONBOARD"}  # ONBOARD has no prompt yet


@pytest.mark.parametrize("row", ROWS, ids=lambda r: r.id)
def test_hints_agree_with_expected_args(row):
    hints = extract_hints(row.turns_original[0])
    for key in ("commodity", "mandi", "quantity_kg"):
        if key in row.expected_args:
            assert hints.get(key) == row.expected_args[key], (row.turns_original[0], hints)
        elif not row.must_refuse and row.expected_intent not in ("RAG",):
            # a hint the row does not expect would override the model wrongly
            assert key not in hints, (row.turns_original[0], hints)
