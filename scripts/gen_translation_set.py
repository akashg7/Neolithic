"""Build the translation check set (100 rows, 50 mr + 50 hi) -> eval/data/translation_100.jsonl.

NOT real farmer sentences. Rows are assembled from two AUTHORED sources already in the repo:
  * the 44 Marathi/Hindi turns of eval/data/agent_eval_60.jsonl (all of them, last turn of each), and
  * 56 phrasings from eval/data/unit_slot.jsonl (28 mr + 28 hi, evenly spaced, deterministic).
`turns_english` is a gloss written to carry the same numbers and entities, NOT a polished reference
translation, so the eval scores number / commodity / mandi / quantity preservation, not fluency.
Fluency is the 40-sample native-speaker rating (eval_translation.py --export-ratings / --ratings).
"""
from __future__ import annotations

import hashlib
import json
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))
from app.contracts import EvalRow  # noqa: E402
from app.nlp.hints import extract_hints  # noqa: E402


def split_of(rid: str) -> str:
    return "dev" if int(hashlib.sha256(rid.encode()).hexdigest(), 16) % 100 < 40 else "test"


def _load(name: str) -> list[dict]:
    return [json.loads(x) for x in (ROOT / "eval/data" / name).read_text("utf-8").splitlines() if x.strip()]


def build() -> list[EvalRow]:
    picked: list[tuple[str, str, str, str]] = []  # (locale, original, english, source)
    for r in _load("agent_eval_60.jsonl"):
        if r["locale"] in ("mr", "hi"):
            picked.append((r["locale"], r["turns_original"][-1], r["turns_english"][-1], "agent_eval"))
    for loc in ("mr", "hi"):
        pool = [r for r in _load("unit_slot.jsonl") if r["locale"] == loc]
        step = len(pool) / 28
        picked += [(loc, pool[int(i * step)]["turns_original"][0], pool[int(i * step)]["turns_english"][0], "unit_slot")
                   for i in range(28)]
    rows, n = [], {"mr": 0, "hi": 0}
    for loc, orig, eng, src in picked:
        n[loc] += 1
        rid = f"tr_{loc}_{n[loc]:02d}"
        hints = {k: v for k, v in extract_hints(orig).items() if k in ("commodity", "mandi", "quantity_kg")}
        rows.append(EvalRow(id=rid, split=split_of(rid), locale=loc, turns_original=[orig], turns_english=[eng],
                            screen_context={"source": src}, expected_intent="TRANSLATION", expected_args=hints))
    return rows


if __name__ == "__main__":
    out = ROOT / "eval/data/translation_100.jsonl"
    rows = build()
    out.write_text("".join(r.model_dump_json() + "\n" for r in rows), "utf-8")
    print(f"wrote {len(rows)} rows -> {out}  mr={sum(r.locale == 'mr' for r in rows)} hi={sum(r.locale == 'hi' for r in rows)} "
          f"dev={sum(r.split == 'dev' for r in rows)} test={sum(r.split == 'test' for r in rows)}")
