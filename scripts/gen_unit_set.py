"""Generate the unit-and-slot eval set (~200 phrasings, mr/hi/en) -> eval/data/unit_slot.jsonl.

Deterministic (seeded). Split is by a stable hash of the id: ~50% dev / ~50% test, so tuning on dev
never touches test. Expected values come from the same units table the parser uses, so this set
checks PARSING of number words, digits, scripts and inflections -- not whether 1 bori really is
50 kg (that is a glossary fact to confirm with the team).
"""
from __future__ import annotations

import hashlib
import json
import random
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))
from app.contracts import EvalRow  # noqa: E402

KG = {"bori": 50, "quintal": 100, "ton": 1000, "kg": 1}
UNIT_FORM = {  # per language: unit -> surface forms
    "mr": {"bori": ["बोरी", "बोऱ्या"], "quintal": ["क्विंटल"], "ton": ["टन"], "kg": ["किलो", "kg"]},
    "hi": {"bori": ["बोरी"], "quintal": ["क्विंटल"], "ton": ["टन"], "kg": ["किलो", "kg"]},
    "en": {"bori": ["bori", "bags"], "quintal": ["quintal", "quintals"], "ton": ["tons"], "kg": ["kg", "kilo"]},
}
NUMS = [  # (value, {lang: [forms]})
    (2, {"mr": ["२", "2", "दोन"], "hi": ["२", "2", "दो"], "en": ["2", "two"]}),
    (5, {"mr": ["५", "5", "पाच"], "hi": ["५", "5", "पाँच"], "en": ["5", "five"]}),
    (10, {"mr": ["१०", "10", "दहा"], "hi": ["१०", "10", "दस"], "en": ["10", "ten"]}),
    (20, {"mr": ["२०", "20", "वीस"], "hi": ["२०", "20", "बीस"], "en": ["20", "twenty"]}),
    (50, {"mr": ["५०", "50", "पन्नास"], "hi": ["५०", "50", "पचास"], "en": ["50", "fifty"]}),
    (100, {"mr": ["१००", "100", "शंभर"], "hi": ["१००", "100", "सौ"], "en": ["100", "hundred"]}),
    (1500, {"mr": ["१५००", "1,500"], "hi": ["१५००", "1,500"], "en": ["1500", "1,500"]}),
]
COMMODITY = {
    "cmd_onion": {"mr": "कांदा", "hi": "प्याज", "en": "onion"},
    "cmd_tomato": {"mr": "टोमॅटो", "hi": "टमाटर", "en": "tomato"},
    "cmd_potato": {"mr": "बटाटा", "hi": "आलू", "en": "potato"},
    "cmd_soybean": {"mr": "सोयाबीन", "hi": "सोयाबीन", "en": "soybean"},
    "cmd_cotton": {"mr": "कापूस", "hi": "कपास", "en": "cotton"},
    "cmd_wheat": {"mr": "गहू", "hi": "गेहूं", "en": "wheat"},
    "cmd_tur": {"mr": "तूर", "hi": "अरहर", "en": "tur"},
    "cmd_chana": {"mr": "हरभरा", "hi": "चना", "en": "chana"},
    "cmd_maize": {"mr": "मका", "hi": "मक्का", "en": "maize"},
    "cmd_turmeric": {"mr": "हळद", "hi": "हल्दी", "en": "turmeric"},
}
MANDI = {
    "mkt_lasalgaon": {"mr": "लासलगाव", "hi": "लासलगांव", "en": "Lasalgaon"},
    "mkt_nashik": {"mr": "नाशिक", "hi": "नासिक", "en": "Nashik"},
    "mkt_pune": {"mr": "पुणे", "hi": "पुणे", "en": "Pune"},
    "mkt_solapur": {"mr": "सोलापूर", "hi": "शोलापुर", "en": "Solapur"},
    "mkt_latur": {"mr": "लातूर", "hi": "लातूर", "en": "Latur"},
    "mkt_akola": {"mr": "अकोला", "hi": "अकोला", "en": "Akola"},
}
# {n} number, {u} unit, {c} commodity, {m} mandi. English reference is built separately.
TEMPLATES = {
    "mr": ["माझ्याकडे {n} {u} {c} आहे, {m} मंडीत विकू का?", "{m} मंडीत {n} {u} {c} विकायचा आहे",
           "{c} {n} {u}, {m} मध्ये भाव काय?", "{n} {u} {c} घेऊन {m} मंडीला जायचे आहे"],
    "hi": ["मेरे पास {n} {u} {c} है, {m} मंडी में बेचूं?", "{m} मंडी में {n} {u} {c} बेचना है",
           "{c} {n} {u}, {m} में भाव क्या है?", "{n} {u} {c} लेकर {m} मंडी जाना है"],
    "en": ["I have {n} {u} of {c}, should I sell at {m}?", "Sell {n} {u} {c} at {m} market",
           "{c} {n} {u}, what is the price at {m}?", "Taking {n} {u} of {c} to {m} mandi"],
}
UNKNOWN_UNIT = {"mr": ["खंडी", "गोणी"], "hi": ["खंडी", "गोनी"], "en": ["khandi", "goni"]}


def split_of(rid: str) -> str:
    return "dev" if int(hashlib.sha1(rid.encode()).hexdigest(), 16) % 2 == 0 else "test"


def build(n_rows: int = 200, seed: int = 7) -> list[EvalRow]:
    rnd = random.Random(seed)
    rows: list[EvalRow] = []
    langs = ["mr", "hi", "en"]
    for i in range(n_rows):
        lang = langs[i % 3]
        unknown = i % 20 == 19
        value, forms = rnd.choice(NUMS)
        num = rnd.choice(forms[lang])
        cid, mid = rnd.choice(list(COMMODITY)), rnd.choice(list(MANDI))
        if unknown:
            unit_key, unit_form = "unknown", rnd.choice(UNKNOWN_UNIT[lang])
        else:
            unit_key = rnd.choice(list(KG))
            unit_form = rnd.choice(UNIT_FORM[lang][unit_key])
        tpl = rnd.choice(TEMPLATES[lang])
        text = tpl.format(n=num, u=unit_form, c=COMMODITY[cid][lang], m=MANDI[mid][lang])
        eng = rnd.choice(TEMPLATES["en"]).format(n=value, u=unit_key if unit_key != "unknown" else unit_form,
                                                 c=COMMODITY[cid]["en"], m=MANDI[mid]["en"])
        rid = f"u_{i:03d}"
        args = {"commodity": cid, "mandi": mid}
        if unknown:
            args["unit_unknown"] = "khandi" if unit_form in ("खंडी", "khandi") else "goni"
        else:
            args["quantity_kg"] = value * KG[unit_key]
        rows.append(EvalRow(id=rid, split=split_of(rid), locale=lang, turns_original=[text], turns_english=[eng],
                            expected_intent="WINDOW", expected_tool="compute_sale_window", expected_args=args))
    return rows


if __name__ == "__main__":
    out = ROOT / "eval/data/unit_slot.jsonl"
    rows = build()
    out.write_text("".join(r.model_dump_json() + "\n" for r in rows), "utf-8")
    print(f"wrote {len(rows)} rows -> {out}  dev={sum(r.split == 'dev' for r in rows)} test={sum(r.split == 'test' for r in rows)}")
