"""Build the 40-prompt model bake-off set (eval/data/bakeoff_40.jsonl).

    python scripts/build_bakeoff.py              # writes the set with reference English
    python scripts/build_bakeoff.py --translate  # also re-translates each prompt through the
                                                 # real translation layer (needs SARVAM_API_KEY)

IMPORTANT: these 40 prompts were AUTHORED (20 Marathi, 20 Hindi) to cover every intent and tool.
They are not recorded farmer queries. Replace or extend them with real ones from the team /
field visits before quoting bake-off numbers as 'real farmer data'.
The plan wants turns_english produced by the SAME layer the app uses: run with --translate on
Day 1 evening once SARVAM_API_KEY is set. Reference translations (written by hand) are kept in
eval/data/bakeoff_40.reference_en.json for comparison.

expected_args use the frozen post-wrapper form (quantity_kg, resolved IDs).
GRADE/NAVIGATE args are provisional until Person A confirms the six assay field names and the
ui_action screen whitelist.
"""
from __future__ import annotations

import argparse
import asyncio
import json
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))

from app.contracts import EvalRow  # noqa: E402

TOOL = {
    "PRICE": "get_price_forecast", "WINDOW": "compute_sale_window", "LOT": "create_lot_draft",
    "GRADE": "calculate_grade", "PORTFOLIO": "get_farmer_portfolio", "RAG": "search_agri_knowledge",
    "NAVIGATE": "navigate_screen",
}

# (id, locale, original, english_reference, intent, args, must_refuse)
P = [
    # ---------------- Marathi
    ("b_m01", "mr", "आज लासलगावला कांद्याचा भाव किती आहे?", "What is the onion price at Lasalgaon today?", "PRICE", {"commodity": "cmd_onion", "mandi": "mkt_lasalgaon"}, False),
    ("b_m02", "mr", "पुढच्या दोन आठवड्यात टोमॅटोचा भाव कसा राहील?", "How will tomato prices look over the next two weeks?", "PRICE", {"commodity": "cmd_tomato", "horizon_days": 14}, False),
    ("b_m03", "mr", "सोयाबीनचा भाव लातूरमध्ये वाढेल का?", "Will the soybean price go up in Latur?", "PRICE", {"commodity": "cmd_soybean", "mandi": "mkt_latur"}, False),
    ("b_m04", "mr", "नाशिक मंडीत आज बटाट्याचा दर काय आहे?", "What is today's potato rate at Nashik mandi?", "PRICE", {"commodity": "cmd_potato", "mandi": "mkt_nashik"}, False),
    ("b_m05", "mr", "माझ्याकडे २० बोरी कांदा आहे, लासलगावला आत्ता विकू की थांबू?", "I have 20 bags of onion. Should I sell now at Lasalgaon or wait?", "WINDOW", {"commodity": "cmd_onion", "mandi": "mkt_lasalgaon", "quantity_kg": 1000}, False),
    ("b_m06", "mr", "दोन क्विंटल हरभरा आहे, सोलापूरला कधी विकणे फायद्याचे ठरेल?", "I have two quintals of chana. When would it be profitable to sell in Solapur?", "WINDOW", {"commodity": "cmd_chana", "mandi": "mkt_solapur", "quantity_kg": 200}, False),
    ("b_m07", "mr", "५ क्विंटल तूर घेऊन अकोल्याला जायचे आहे, आता जाऊ का?", "I want to take 5 quintals of tur to Akola. Should I go now?", "WINDOW", {"commodity": "cmd_tur", "mandi": "mkt_akola", "quantity_kg": 500}, False),
    ("b_m08", "mr", "साडेतीन टन डाळिंब आहे, पुण्यात कधी विकू?", "I have three and a half tons of pomegranate. When should I sell in Pune?", "WINDOW", {"commodity": "cmd_pomegranate", "mandi": "mkt_pune", "quantity_kg": 3500}, False),
    ("b_m09", "mr", "मला १० क्विंटल गहू विक्रीसाठी टाकायचा आहे", "I want to list 10 quintals of wheat for sale.", "LOT", {"commodity": "cmd_wheat", "quantity_kg": 1000}, False),
    ("b_m10", "mr", "३० बोरी कांद्याचा लॉट तयार कर, अपेक्षित भाव १८०० रुपये क्विंटल", "Create a lot of 30 bags of onion, expected price 1800 rupees per quintal.", "LOT", {"commodity": "cmd_onion", "quantity_kg": 1500, "expected_price": 1800}, False),
    ("b_m11", "mr", "माझ्या कांद्याला कोणती ग्रेड मिळेल?", "Which grade will my onion get?", "GRADE", {"commodity": "cmd_onion"}, False),
    ("b_m12", "mr", "माझ्या सोयाबीनची ग्रेड तपासायची आहे", "I want to check the grade of my soybean.", "GRADE", {"commodity": "cmd_soybean"}, False),
    ("b_m13", "mr", "माझे सध्याचे लॉट आणि ऑफर्स दाखव", "Show my current lots and offers.", "PORTFOLIO", {}, False),
    ("b_m14", "mr", "माझ्या ऑफरचे पैसे एस्क्रोमध्ये आले का?", "Has the money for my offer reached escrow?", "PORTFOLIO", {}, False),
    ("b_m15", "mr", "किसान क्रेडिट कार्डसाठी कोण पात्र आहे?", "Who is eligible for a Kisan Credit Card?", "RAG", {"category": "schemes_finance"}, False),
    ("b_m16", "mr", "या प्लॅटफॉर्मवर माल कसा विकायचा?", "How do I sell produce on this platform?", "RAG", {"category": "platform"}, False),
    ("b_m17", "mr", "शेतमालावर कर्ज कसे मिळते?", "How can I get a loan against my produce?", "RAG", {"category": "schemes_finance"}, False),
    ("b_m18", "mr", "मला प्रोफाइल पेज उघडून दे", "Open the profile page for me.", "NAVIGATE", {"target_screen": "profile"}, False),
    ("b_m19", "mr", "कांद्यावरील करपा रोगासाठी कोणत्या कीटकनाशकाची किती फवारणी करू?", "Which pesticide and how much should I spray for blight on onion?", "OUT_OF_SCOPE", {}, True),
    ("b_m20", "mr", "नमस्कार, कसे आहात?", "Hello, how are you?", "SMALLTALK", {}, False),
    # ---------------- Hindi
    ("b_h01", "hi", "आज नासिक मंडी में प्याज का भाव क्या है?", "What is the onion price at Nashik mandi today?", "PRICE", {"commodity": "cmd_onion", "mandi": "mkt_nashik"}, False),
    ("b_h02", "hi", "अगले हफ्ते टमाटर के दाम बढ़ेंगे या घटेंगे?", "Will tomato prices go up or down next week?", "PRICE", {"commodity": "cmd_tomato", "horizon_days": 7}, False),
    ("b_h03", "hi", "पुणे मंडी में आलू का रेट बताइए", "Tell me the potato rate at Pune mandi.", "PRICE", {"commodity": "cmd_potato", "mandi": "mkt_pune"}, False),
    ("b_h04", "hi", "कपास का भाव अकोला में कितना है?", "What is the cotton price in Akola?", "PRICE", {"commodity": "cmd_cotton", "mandi": "mkt_akola"}, False),
    ("b_h05", "hi", "मेरे पास 50 बोरी प्याज है, क्या अभी लासलगांव में बेच दूं?", "I have 50 bags of onion. Should I sell now at Lasalgaon?", "WINDOW", {"commodity": "cmd_onion", "mandi": "mkt_lasalgaon", "quantity_kg": 2500}, False),
    ("b_h06", "hi", "3 क्विंटल चना है, नागपुर में कब बेचना ठीक रहेगा?", "I have 3 quintals of chana. When is it best to sell in Nagpur?", "WINDOW", {"commodity": "cmd_chana", "mandi": "mkt_nagpur", "quantity_kg": 300}, False),
    ("b_h07", "hi", "दो टन गेहूं है, जलगांव मंडी भेजूं या रुकूं?", "I have two tons of wheat. Should I send it to Jalgaon mandi or wait?", "WINDOW", {"commodity": "cmd_wheat", "mandi": "mkt_jalgaon", "quantity_kg": 2000}, False),
    ("b_h08", "hi", "डेढ़ क्विंटल हल्दी है, सांगली में कब बेचूं?", "I have one and a half quintals of turmeric. When should I sell in Sangli?", "WINDOW", {"commodity": "cmd_turmeric", "mandi": "mkt_sangli", "quantity_kg": 150}, False),
    ("b_h09", "hi", "मुझे 20 क्विंटल मक्का बिक्री के लिए डालना है", "I want to list 20 quintals of maize for sale.", "LOT", {"commodity": "cmd_maize", "quantity_kg": 2000}, False),
    ("b_h10", "hi", "10 बोरी लहसुन का लॉट बना दो", "Create a lot of 10 bags of garlic.", "LOT", {"commodity": "cmd_garlic", "quantity_kg": 500}, False),
    ("b_h11", "hi", "मेरे प्याज की ग्रेड क्या होगी?", "What grade will my onion get?", "GRADE", {"commodity": "cmd_onion"}, False),
    ("b_h12", "hi", "गेहूं की ग्रेड चेक करनी है", "I want to check the grade of my wheat.", "GRADE", {"commodity": "cmd_wheat"}, False),
    ("b_h13", "hi", "मेरे अभी के लॉट और ऑफर दिखाओ", "Show my current lots and offers.", "PORTFOLIO", {}, False),
    ("b_h14", "hi", "मेरे ऑफर का पैसा एस्क्रो में आया क्या?", "Has the money for my offer reached escrow?", "PORTFOLIO", {}, False),
    ("b_h15", "hi", "फसल बीमा के लिए कैसे आवेदन करें?", "How do I apply for crop insurance?", "RAG", {"category": "schemes_finance"}, False),
    ("b_h16", "hi", "प्लेटफॉर्म पर माल बेचने के लिए क्या दस्तावेज़ चाहिए?", "What documents are needed to sell produce on the platform?", "RAG", {"category": "platform"}, False),
    ("b_h17", "hi", "ग्रेड A प्याज की क्या पहचान होती है?", "How do you recognise Grade A onion?", "RAG", {"category": "grading", "crop": "onion"}, False),
    ("b_h18", "hi", "मुझे बिक्री वाला पेज खोलकर दिखाओ", "Open the sell page and show me.", "NAVIGATE", {"target_screen": "sell"}, False),
    ("b_h19", "hi", "टमाटर में कीड़े लग गए हैं, कौन सी दवा कितनी डालूं?", "Pests have attacked my tomatoes. Which medicine should I use and how much?", "OUT_OF_SCOPE", {}, True),
    ("b_h20", "hi", "आज क्रिकेट मैच का स्कोर क्या है?", "What is the cricket match score today?", "OUT_OF_SCOPE", {}, False),
]


def rows(english_override: dict[str, str] | None = None) -> list[EvalRow]:
    out = []
    for pid, loc, orig, eng, intent, args, refuse in P:
        out.append(EvalRow(
            id=pid, split="dev", locale=loc, turns_original=[orig],
            turns_english=[(english_override or {}).get(pid, eng)],
            expected_intent=intent, expected_tool=TOOL.get(intent, "final_answer"),
            expected_args=args, must_refuse=refuse,
        ))
    return out


async def translate_all() -> dict[str, str]:
    from app.nlp.translate import to_english
    res = await asyncio.gather(*(to_english(text=o, locale_hint=l) for _, l, o, *_ in P))
    return {P[i][0]: r.english for i, r in enumerate(res)}


def main() -> None:
    ap = argparse.ArgumentParser()
    ap.add_argument("--translate", action="store_true", help="use the real translation layer for turns_english")
    ap.add_argument("--out", default=str(ROOT / "eval/data/bakeoff_40.jsonl"))
    a = ap.parse_args()
    ref = {pid: eng for pid, _, _, eng, *_ in P}
    (ROOT / "eval/data/bakeoff_40.reference_en.json").write_text(json.dumps(ref, ensure_ascii=False, indent=1), "utf-8")
    override = asyncio.run(translate_all()) if a.translate else None
    data = rows(override)
    Path(a.out).write_text("".join(r.model_dump_json() + "\n" for r in data), "utf-8")
    print(f"wrote {len(data)} rows -> {a.out}" + (" (English via translation layer)" if a.translate else " (reference English)"))


if __name__ == "__main__":
    main()
