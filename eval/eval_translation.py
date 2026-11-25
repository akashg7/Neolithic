"""Translation check: do numbers and farm terms survive the English pivot, in both directions?

    # real: needs SARVAM_API_KEY and TRANSLATE_BACKEND=sarvam
    TRANSLATE_BACKEND=sarvam python eval/eval_translation.py --split test --out eval/results/translation_test.json
    # 40 sentences for native speakers to rate (written as CSV):
    TRANSLATE_BACKEND=sarvam python eval/eval_translation.py --export-ratings eval/results/naturalness_sheet.csv
    # after they fill the `natural` column with 1 / 0:
    python eval/eval_translation.py --ratings eval/results/naturalness_sheet.csv

Forward  (mr/hi -> English, `to_english`)   numbers preserved; commodity, mandi and quantity_kg the same
                                            when the unit parser reads the ENGLISH output vs the original.
Backward (reference English -> mr/hi, `translate_back_checked`)  numbers preserved; commodity and mandi
                                            still recognised in the farmer's language.
Plan targets: farm terms and numbers preserved; >= 80% of rated replies natural. With the default
stub backend nothing is translated, so the script refuses to report numbers from it.
"""
from __future__ import annotations

import argparse
import asyncio
import csv
import json
import os
import statistics
import sys
import time
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))
from app.contracts import EvalRow  # noqa: E402
from app.nlp import translate as tr  # noqa: E402
from app.nlp.hints import extract_hints  # noqa: E402
from app.nlp.numbers import numbers_preserved  # noqa: E402

DEFAULT_SET = ROOT / "eval/data/translation_100.jsonl"
RATING_SENTENCES = [  # authored English agent-style replies, translated to both languages for rating
    "Hold for 5 days. The expected gain is Rs 1850 and in the worst 1-in-10 case it is Rs 400.",
    "Sell now. Waiting 7 days is not worth the extra storage cost for your 20 bori of onion.",
    "I cannot give reliable advice right now because the price forecast is too uncertain.",
    "Today's onion price at Lasalgaon is Rs 2150 per quintal, up 2.5 percent this week.",
    "Your soybean is Grade B. Dry it for one more day to reach Grade A.",
    "Please tell me the quantity in kg, quintals or bori. Khandi can mean different weights.",
    "I have prepared a lot of 10 quintals of onion. Tap Confirm to save it.",
    "You have 2 active lots and 1 open offer. Do you want to see the offer?",
    "The Kisan Credit Card gives short-term crop loans. Ask your bank which limit applies to you.",
    "For pesticide doses please contact your local Krishi Vigyan Kendra.",
    "A pledge loan is only shown when the expected gain is higher than the interest.",
    "The buyer's money stays in escrow until you dispatch and the buyer inspects the goods.",
    "You can counter an offer up to 3 times. After that you must accept or reject.",
    "Soybean with moisture up to 10 percent can reach the best grade.",
    "Tomato prices in Pune are uncertain this week, so I will not advise you to hold or sell.",
    "Open the deals screen to see the status of your offers.",
    "Your 50 quintals of wheat could earn about Rs 4200 more if you wait 6 days.",
    "I did not understand the crop name. Which crop do you want to sell?",
    "PM-KISAN pays Rs 6000 a year in three instalments of Rs 2000.",
    "Thank you. Let me know if you want to check another mandi.",
]


def load_rows(path: Path, split: str) -> list[EvalRow]:
    rows = [EvalRow(**json.loads(x)) for x in path.read_text("utf-8").splitlines() if x.strip()]
    return rows if split == "all" else [r for r in rows if r.split == split]


def _rate(xs: list[bool]) -> float | None:
    return round(sum(xs) / len(xs), 4) if xs else None


def _p95(xs: list[float]) -> float | None:
    s = sorted(xs)
    return round(s[min(len(s) - 1, int(round(0.95 * (len(s) - 1))))], 1) if s else None


async def evaluate(rows: list[EvalRow], to_english=tr.to_english, back=tr.translate_back_checked) -> dict:
    fwd = {"numbers": [], "commodity": [], "mandi": [], "quantity_kg": []}
    bwd = {"numbers": [], "commodity": [], "mandi": []}
    f_ms, b_ms, failures = [], [], []
    by_lang: dict[str, dict] = {}
    for r in rows:
        orig, ref_en = r.turns_original[0], r.turns_english[0]
        exp = r.expected_args
        lang = by_lang.setdefault(r.locale, {"fwd_numbers": [], "bwd_numbers": []})
        try:
            t0 = time.perf_counter()
            t = await to_english(text=orig, locale_hint=r.locale)
            f_ms.append((time.perf_counter() - t0) * 1000)
            eng_hints = extract_hints(t.english)
            ok_n = numbers_preserved(orig, t.english)
            fwd["numbers"].append(ok_n)
            lang["fwd_numbers"].append(ok_n)
            for k in ("commodity", "mandi", "quantity_kg"):
                if k in exp:
                    fwd[k].append(eng_hints.get(k) == exp[k])
            if not ok_n:
                failures.append({"id": r.id, "dir": "forward", "original": orig, "english": t.english})
        except Exception as e:
            failures.append({"id": r.id, "dir": "forward", "error": f"{type(e).__name__}: {str(e)[:120]}"})
            fwd["numbers"].append(False)
            lang["fwd_numbers"].append(False)
        try:
            t0 = time.perf_counter()
            (out,), ok = await back([ref_en], r.locale)
            b_ms.append((time.perf_counter() - t0) * 1000)
            ok_n = bool(ok) and numbers_preserved(ref_en, out)
            bwd["numbers"].append(ok_n)
            lang["bwd_numbers"].append(ok_n)
            back_hints = extract_hints(out)
            for k in ("commodity", "mandi"):
                if k in exp:
                    bwd[k].append(back_hints.get(k) == exp[k])
            if not ok_n:
                failures.append({"id": r.id, "dir": "backward", "english": ref_en, "translated": out})
        except Exception as e:
            failures.append({"id": r.id, "dir": "backward", "error": f"{type(e).__name__}: {str(e)[:120]}"})
            bwd["numbers"].append(False)
            lang["bwd_numbers"].append(False)
    return {"n": len(rows),
            "forward": {k: {"n": len(v), "rate": _rate(v)} for k, v in fwd.items()},
            "backward": {k: {"n": len(v), "rate": _rate(v)} for k, v in bwd.items()},
            "by_language": {k: {m: _rate(v) for m, v in d.items()} for k, d in sorted(by_lang.items())},
            "latency_ms": {"forward_median": round(statistics.median(f_ms), 1) if f_ms else None, "forward_p95": _p95(f_ms),
                           "backward_median": round(statistics.median(b_ms), 1) if b_ms else None, "backward_p95": _p95(b_ms)},
            "failures": failures}


async def export_ratings(path: Path, back=tr.from_english) -> int:
    rows = []
    for lang in ("mr", "hi"):
        outs = await back(RATING_SENTENCES, lang)
        for i, (en, out) in enumerate(zip(RATING_SENTENCES, outs), start=1):
            rows.append({"id": f"rate_{lang}_{i:02d}", "lang": lang, "english": en, "translation": out, "natural": "", "note": ""})
    with path.open("w", newline="", encoding="utf-8") as f:
        w = csv.DictWriter(f, fieldnames=list(rows[0]))
        w.writeheader()
        w.writerows(rows)
    return len(rows)


def summarise_ratings(path: Path) -> dict:
    with path.open(newline="", encoding="utf-8") as f:
        rows = list(csv.DictReader(f))
    rated = [r for r in rows if r["natural"].strip() in ("0", "1")]
    out = {"rows": len(rows), "rated": len(rated), "unrated": len(rows) - len(rated)}
    for lang in ("mr", "hi", "all"):
        sel = [r for r in rated if lang == "all" or r["lang"] == lang]
        out[lang] = {"n": len(sel), "natural_rate": round(sum(r["natural"].strip() == "1" for r in sel) / len(sel), 4) if sel else None}
    out["target_met_ge_0_80"] = bool(rated) and out["all"]["natural_rate"] >= 0.80 and out["unrated"] == 0
    return out


def main() -> None:
    ap = argparse.ArgumentParser()
    ap.add_argument("--set", type=Path, default=DEFAULT_SET)
    ap.add_argument("--split", choices=["dev", "test", "all"], default="test")
    ap.add_argument("--out", type=Path, default=None)
    ap.add_argument("--export-ratings", type=Path, default=None)
    ap.add_argument("--ratings", type=Path, default=None)
    a = ap.parse_args()
    if a.ratings:
        print(json.dumps(summarise_ratings(a.ratings), indent=2))
        return
    if tr.backend() == "stub":
        sys.exit("TRANSLATE_BACKEND is 'stub': nothing would be translated. Set TRANSLATE_BACKEND=sarvam and SARVAM_API_KEY.")
    if a.export_ratings:
        n = asyncio.run(export_ratings(a.export_ratings))
        print(f"wrote {n} sentences for native-speaker rating -> {a.export_ratings} (fill `natural` with 1 or 0)")
        return
    report = {"split": a.split, "backend": tr.backend(), "model": os.getenv("SARVAM_TRANSLATE_MODEL", "mayura:v1"),
              "result": asyncio.run(evaluate(load_rows(a.set, a.split)))}
    text = json.dumps(report, ensure_ascii=False, indent=2)
    print(text)
    if a.out:
        a.out.write_text(text + "\n", "utf-8")


if __name__ == "__main__":
    main()
