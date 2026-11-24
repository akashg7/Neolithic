import importlib.util
import json
import sys
from pathlib import Path

from app.contracts import EvalRow

ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(ROOT))
from eval.eval_units import evaluate  # noqa: E402

spec = importlib.util.spec_from_file_location("gen_unit_set", ROOT / "scripts/gen_unit_set.py")
gen = importlib.util.module_from_spec(spec)
spec.loader.exec_module(gen)

ROWS = [EvalRow(**json.loads(x)) for x in (ROOT / "eval/data/unit_slot.jsonl").read_text("utf-8").splitlines()]


def test_committed_set_matches_generator():
    assert [r.model_dump() for r in gen.build()] == [r.model_dump() for r in ROWS]


def test_split_is_roughly_balanced_and_disjoint():
    dev = [r for r in ROWS if r.split == "dev"]
    test = [r for r in ROWS if r.split == "test"]
    assert len(ROWS) == 200 and 70 <= len(dev) <= 130 and not ({r.id for r in dev} & {r.id for r in test})


def test_targets_on_generated_set():
    for split in ("dev", "test"):
        res = evaluate([r for r in ROWS if r.split == split])
        assert res["unit_conversion_known"]["accuracy"] == 1.0        # plan: 100% on known units
        assert res["unknown_unit_flagged"]["accuracy"] == 1.0         # unknown units are flagged, never guessed
        assert res["slot_f1_micro"] > 0.88                            # plan: slot F1 above 88%
