"""Slot F1 for the unit-and-slot set: commodity, mandi, quantity_kg read from ORIGINAL text.

    python eval/eval_units.py --split test [--show-errors]

Targets (plan): unit conversion 100% on known units; unknown units flagged (asks the farmer);
slot F1 above 88%. Report only the test split in the final numbers; tune on dev.
"""
from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))
from app.contracts import EvalRow  # noqa: E402
from app.nlp.hints import extract_hints  # noqa: E402

SLOTS = ("commodity", "mandi", "quantity_kg")


def evaluate(rows: list[EvalRow]) -> dict:
    tp = {s: 0 for s in SLOTS}
    fp = {s: 0 for s in SLOTS}
    fn = {s: 0 for s in SLOTS}
    known = known_ok = unk = unk_ok = 0
    errors = []
    for r in rows:
        h = extract_hints(r.turns_original[0])
        for s in SLOTS:
            exp, got = r.expected_args.get(s), h.get(s)
            if exp is not None and got == exp:
                tp[s] += 1
            else:
                if got is not None:
                    fp[s] += 1
                if exp is not None:
                    fn[s] += 1
                if exp != got:
                    errors.append({"id": r.id, "slot": s, "expected": exp, "got": got, "text": r.turns_original[0]})
        if "quantity_kg" in r.expected_args:
            known += 1
            known_ok += h.get("quantity_kg") == r.expected_args["quantity_kg"]
        if "unit_unknown" in r.expected_args:
            unk += 1
            unk_ok += h.get("unit_unknown") == r.expected_args["unit_unknown"] and "quantity_kg" not in h
    per = {}
    for s in SLOTS:
        p = tp[s] / (tp[s] + fp[s]) if tp[s] + fp[s] else 0.0
        rc = tp[s] / (tp[s] + fn[s]) if tp[s] + fn[s] else 0.0
        per[s] = {"precision": round(p, 4), "recall": round(rc, 4), "f1": round(2 * p * rc / (p + rc), 4) if p + rc else 0.0}
    micro_tp, micro_fp, micro_fn = sum(tp.values()), sum(fp.values()), sum(fn.values())
    mp = micro_tp / (micro_tp + micro_fp) if micro_tp + micro_fp else 0.0
    mr_ = micro_tp / (micro_tp + micro_fn) if micro_tp + micro_fn else 0.0
    return {
        "n": len(rows), "slots": per,
        "slot_f1_micro": round(2 * mp * mr_ / (mp + mr_), 4) if mp + mr_ else 0.0,
        "unit_conversion_known": {"n": known, "accuracy": round(known_ok / known, 4) if known else None},
        "unknown_unit_flagged": {"n": unk, "accuracy": round(unk_ok / unk, 4) if unk else None},
        "errors": errors,
    }


def main() -> None:
    ap = argparse.ArgumentParser()
    ap.add_argument("--data", default=str(ROOT / "eval/data/unit_slot.jsonl"))
    ap.add_argument("--split", default="test", choices=["dev", "test", "all"])
    ap.add_argument("--show-errors", action="store_true")
    a = ap.parse_args()
    rows = [EvalRow(**json.loads(x)) for x in Path(a.data).read_text("utf-8").splitlines() if x.strip()]
    if a.split != "all":
        rows = [r for r in rows if r.split == a.split]
    res = evaluate(rows)
    errs = res.pop("errors")
    print(json.dumps(res, ensure_ascii=False, indent=1))
    if a.show_errors:
        for e in errs:
            print(e)


if __name__ == "__main__":
    main()
