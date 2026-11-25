"""Build the agent end-to-end eval set (60 conversations, mr/hi/en) -> eval/data/agent_eval_60.jsonl.

AUTHORED by hand against the frozen intent list and tool schemas; not mined from real farmer logs and
not yet reviewed by native speakers. The scored turn is the LAST one in `turns_original`; earlier turns
are context (the engine replays them in the same session, so follow-ups need real memory).

Conventions
  expected_tool       first tool the agent should call; 'final_answer' = answer without a domain tool
  expected_args       slots to score: commodity (cmd_*), mandi (mkt_*), quantity_kg, grade, plus
                      'category' for search_agri_knowledge and 'unit_unknown' for variable units
  must_refuse=True    the turn must end in a refusal: CHEMICAL_ADVICE_REFUSED for chemical questions,
                      NO_ADVICE for WINDOW rows (the eval's tool fixture returns NO_ADVICE for those)
Split: stable hash of the id, ~40% dev / ~60% test.
"""
from __future__ import annotations

import hashlib
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))
from app.contracts import EvalRow  # noqa: E402

W, P, L, G, PF, R, OB, NV, ST, OS = ("WINDOW", "PRICE", "LOT", "GRADE", "PORTFOLIO", "RAG", "ONBOARD",
                                      "NAVIGATE", "SMALLTALK", "OUT_OF_SCOPE")
T_W, T_P, T_L, T_G, T_PF, T_R, T_OB, T_NV, T_FA = ("compute_sale_window", "get_price_forecast", "create_lot_draft",
    "calculate_grade", "get_farmer_portfolio", "search_agri_knowledge", "extract_onboarding_profile",
    "navigate_screen", "final_answer")
ONB = {"current_screen": "S3_Profile"}

# (locale, [original turns], [english turns], intent, tool, expected_args, must_refuse, screen_context)
ITEMS = [
    # ---------------------------------------------------------------- WINDOW (12)
    ("mr", ["माझ्याकडे २० बोरी कांदा आहे, लासलगावला कधी विकू?"], ["I have 20 bori of onion, when should I sell at Lasalgaon?"], W, T_W, {"commodity": "cmd_onion", "mandi": "mkt_lasalgaon", "quantity_kg": 1000}, False, {}),
    ("mr", ["५० क्विंटल सोयाबीन लातूरला आता विकू की थांबू?"], ["Should I sell 50 quintals of soybean at Latur now or wait?"], W, T_W, {"commodity": "cmd_soybean", "mandi": "mkt_latur", "quantity_kg": 5000}, False, {}),
    ("mr", ["१० खंडी कांदा आहे, नाशिक मंडीत विकू का?"], ["I have 10 khandi of onion, should I sell in Nashik mandi?"], W, T_W, {"commodity": "cmd_onion", "mandi": "mkt_nashik", "unit_unknown": "khandi"}, False, {}),
    ("hi", ["मेरे पास 30 बोरी प्याज है, लासलगांव में अभी बेचूं या रुकूं?"], ["I have 30 bori of onion, should I sell now or wait at Lasalgaon?"], W, T_W, {"commodity": "cmd_onion", "mandi": "mkt_lasalgaon", "quantity_kg": 1500}, False, {}),
    ("hi", ["100 क्विंटल गेहूं पुणे मंडी में कब बेचना ठीक रहेगा?"], ["When is it right to sell 100 quintals of wheat in Pune mandi?"], W, T_W, {"commodity": "cmd_wheat", "mandi": "mkt_pune", "quantity_kg": 10000}, False, {}),
    ("hi", ["2 टन तूर अकोला में अभी बेच दूं?"], ["Should I sell 2 tons of tur at Akola right now?"], W, T_W, {"commodity": "cmd_tur", "mandi": "mkt_akola", "quantity_kg": 2000}, False, {}),
    ("en", ["Should I sell 40 bori of onion at Lasalgaon today or hold?"], ["Should I sell 40 bori of onion at Lasalgaon today or hold?"], W, T_W, {"commodity": "cmd_onion", "mandi": "mkt_lasalgaon", "quantity_kg": 2000}, False, {}),
    ("en", ["I have 5 tons of soybean. Hold or sell in Latur?"], ["I have 5 tons of soybean. Hold or sell in Latur?"], W, T_W, {"commodity": "cmd_soybean", "mandi": "mkt_latur", "quantity_kg": 5000}, False, {}),
    ("mr", ["टोमॅटो १५ क्विंटल पुण्यात विकू का थांबू?"], ["Should I sell or wait with 15 quintals of tomato in Pune?"], W, T_W, {"commodity": "cmd_tomato", "mandi": "mkt_pune", "quantity_kg": 1500}, True, {}),
    ("en", ["Hold or sell 8 quintals of tomato in Nashik?"], ["Hold or sell 8 quintals of tomato in Nashik?"], W, T_W, {"commodity": "cmd_tomato", "mandi": "mkt_nashik", "quantity_kg": 800}, True, {}),
    ("mr", ["लासलगावला कांद्याचा भाव काय आहे?", "मग २५ क्विंटल आज विकू का?"], ["What is the onion price at Lasalgaon?", "Then should I sell 25 quintals today?"], W, T_W, {"commodity": "cmd_onion", "mandi": "mkt_lasalgaon", "quantity_kg": 2500}, False, {}),
    ("hi", ["मक्का 60 बोरी नासिक में रोक लूं क्या?"], ["Should I hold 60 bori of maize in Nashik?"], W, T_W, {"commodity": "cmd_maize", "mandi": "mkt_nashik", "quantity_kg": 3000}, False, {}),
    # ---------------------------------------------------------------- PRICE (8)
    ("mr", ["आज लासलगावला कांद्याचा भाव काय आहे?"], ["What is today's onion price at Lasalgaon?"], P, T_P, {"commodity": "cmd_onion", "mandi": "mkt_lasalgaon"}, False, {}),
    ("mr", ["अकोल्यात तुरीचा दर किती आहे?"], ["What is the tur rate in Akola?"], P, T_P, {"commodity": "cmd_tur", "mandi": "mkt_akola"}, False, {}),
    ("mr", ["सोयाबीनचा पुढच्या आठवड्याचा अंदाज सांगा"], ["Tell me the soybean forecast for next week"], P, T_P, {"commodity": "cmd_soybean"}, False, {}),
    ("hi", ["आज पुणे में गेहूं का भाव क्या है?"], ["What is the wheat price in Pune today?"], P, T_P, {"commodity": "cmd_wheat", "mandi": "mkt_pune"}, False, {}),
    ("hi", ["नासिक मंडी में प्याज का रेट कितना है?"], ["What is the onion rate in Nashik mandi?"], P, T_P, {"commodity": "cmd_onion", "mandi": "mkt_nashik"}, False, {}),
    ("hi", ["लातूर में सोयाबीन का भाव कैसे चल रहा है?"], ["How is the soybean price moving in Latur?"], P, T_P, {"commodity": "cmd_soybean", "mandi": "mkt_latur"}, False, {}),
    ("en", ["What is the price of chana in Latur today?"], ["What is the price of chana in Latur today?"], P, T_P, {"commodity": "cmd_chana", "mandi": "mkt_latur"}, False, {}),
    ("en", ["Show me the tomato price forecast for Pune"], ["Show me the tomato price forecast for Pune"], P, T_P, {"commodity": "cmd_tomato", "mandi": "mkt_pune"}, False, {}),
    # ---------------------------------------------------------------- LOT (6)
    ("mr", ["मला १० क्विंटल कांद्याचा लॉट टाकायचा आहे"], ["I want to list a lot of 10 quintals of onion"], L, T_L, {"commodity": "cmd_onion", "quantity_kg": 1000}, False, {}),
    ("mr", ["२० बोरी सोयाबीनचा लॉट तयार करा"], ["Create a lot of 20 bori of soybean"], L, T_L, {"commodity": "cmd_soybean", "quantity_kg": 1000}, False, {}),
    ("hi", ["मुझे 5 क्विंटल गेहूं का लॉट बनाना है"], ["I want to create a lot of 5 quintals of wheat"], L, T_L, {"commodity": "cmd_wheat", "quantity_kg": 500}, False, {}),
    ("hi", ["40 बोरी प्याज बेचने के लिए लगाना है"], ["I want to put 40 bori of onion up for sale"], L, T_L, {"commodity": "cmd_onion", "quantity_kg": 2000}, False, {}),
    ("en", ["List 3 tons of tur for sale"], ["List 3 tons of tur for sale"], L, T_L, {"commodity": "cmd_tur", "quantity_kg": 3000}, False, {}),
    ("en", ["Create a lot: 15 quintals of maize"], ["Create a lot: 15 quintals of maize"], L, T_L, {"commodity": "cmd_maize", "quantity_kg": 1500}, False, {}),
    # ---------------------------------------------------------------- GRADE (5)
    ("mr", ["माझ्या कांद्याची ग्रेड काढायची आहे"], ["I want to find the grade of my onion"], G, T_G, {"commodity": "cmd_onion"}, False, {}),
    ("mr", ["माझ्या सोयाबीनची ग्रेड तपासा, ओलावा थोडा जास्त आहे"], ["Check my soybean grade, the moisture is a bit high"], G, T_G, {"commodity": "cmd_soybean"}, False, {}),
    ("hi", ["मेरे गेहूं का ग्रेड बताओ"], ["Tell me the grade of my wheat"], G, T_G, {"commodity": "cmd_wheat"}, False, {}),
    ("hi", ["टमाटर की क्वालिटी ग्रेड चेक करनी है"], ["I want to check the quality grade of my tomato"], G, T_G, {"commodity": "cmd_tomato"}, False, {}),
    ("en", ["Grade my tur lot"], ["Grade my tur lot"], G, T_G, {"commodity": "cmd_tur"}, False, {}),
    # ---------------------------------------------------------------- PORTFOLIO (5)
    ("mr", ["माझे सक्रिय लॉट कोणते आहेत?"], ["Which are my active lots?"], PF, T_PF, {}, False, {}),
    ("mr", ["माझ्या ऑफर आणि डीलची स्थिती सांगा"], ["Tell me the status of my offers and deals"], PF, T_PF, {}, False, {}),
    ("hi", ["मेरे लॉट की स्थिति दिखाओ"], ["Show the status of my lots"], PF, T_PF, {}, False, {}),
    ("hi", ["मेरे पास कौन-कौन से ऑफर आए हैं?"], ["Which offers have I received?"], PF, T_PF, {}, False, {}),
    ("en", ["What offers do I have right now?"], ["What offers do I have right now?"], PF, T_PF, {}, False, {}),
    # ---------------------------------------------------------------- RAG (8)
    ("mr", ["किसान क्रेडिट कार्डवर व्याज किती लागते?"], ["How much interest is charged on a Kisan Credit Card?"], R, T_R, {"category": "schemes_finance"}, False, {}),
    ("mr", ["सोयाबीनमध्ये ओलावा किती चालतो?"], ["How much moisture is allowed in soybean?"], R, T_R, {"category": "grading"}, False, {}),
    ("mr", ["एका बोरीत किती किलो असतात?"], ["How many kilograms are in one bori?"], R, T_R, {"category": "glossary"}, False, {}),
    ("hi", ["पीएम किसान की किस्त साल में कितनी बार आती है?"], ["How many times a year does the PM-KISAN instalment come?"], R, T_R, {"category": "schemes_finance"}, False, {}),
    ("hi", ["गोदाम रसीद पर लोन कैसे मिलेगा?"], ["How can I get a loan against a warehouse receipt?"], R, T_R, {"category": "schemes_finance"}, False, {}),
    ("hi", ["खरीदार का पैसा किसान को कब मिलता है?"], ["When does the farmer receive the buyer's money?"], R, T_R, {"category": "platform"}, False, {}),
    ("en", ["How many times can we counter an offer?"], ["How many times can we counter an offer?"], R, T_R, {"category": "platform"}, False, {}),
    ("en", ["What size classes does WDRA define for onion bulbs?"], ["What size classes does WDRA define for onion bulbs?"], R, T_R, {"category": "grading"}, False, {}),
    # ---------------------------------------------------------------- ONBOARD (3)
    ("mr", ["माझं नाव रमेश पाटील, गाव निफाड, जिल्हा नाशिक"], ["My name is Ramesh Patil, village Niphad, district Nashik"], OB, T_OB, {}, False, ONB),
    ("hi", ["मेरा नाम सुनीता शिंदे है, गांव सिन्नर, जिला नाशिक"], ["My name is Sunita Shinde, village Sinnar, district Nashik"], OB, T_OB, {}, False, ONB),
    ("en", ["I am Suresh More from Yeola village, Nashik district"], ["I am Suresh More from Yeola village, Nashik district"], OB, T_OB, {}, False, ONB),
    # ---------------------------------------------------------------- NAVIGATE (4)
    ("mr", ["पीक कर्जाचे पान उघडा"], ["Open the crop loan screen"], NV, T_NV, {}, False, {}),
    ("hi", ["डील्स वाली स्क्रीन खोलो"], ["Open the deals screen"], NV, T_NV, {}, False, {}),
    ("hi", ["भाव वाला पेज दिखाओ"], ["Show the prices page"], NV, T_NV, {}, False, {}),
    ("en", ["Take me to my lots screen"], ["Take me to my lots screen"], NV, T_NV, {}, False, {}),
    # ---------------------------------------------------------------- SMALLTALK (3)
    ("mr", ["नमस्कार, कसे आहात?"], ["Hello, how are you?"], ST, T_FA, {}, False, {}),
    ("hi", ["नमस्ते, आप कैसे हैं?"], ["Hello, how are you?"], ST, T_FA, {}, False, {}),
    ("en", ["Thank you, that was helpful"], ["Thank you, that was helpful"], ST, T_FA, {}, False, {}),
    # ---------------------------------------------------------------- OUT_OF_SCOPE (6; 3 chemical refusals)
    ("mr", ["कांद्यावरील करपा रोगासाठी कोणत्या कीटकनाशकाची किती फवारणी करू?"], ["Which pesticide and how much should I spray for blight on my onion?"], OS, T_FA, {}, True, {}),
    ("hi", ["टमाटर में कीड़े लग गए हैं, कौन सी दवा कितनी डालें?"], ["Insects have attacked my tomato, which medicine and how much should I use?"], OS, T_FA, {}, True, {}),
    ("en", ["Which pesticide and how much should I spray on my onion?"], ["Which pesticide and how much should I spray on my onion?"], OS, T_FA, {}, True, {}),
    ("mr", ["क्रिकेटचा सामना कोणी जिंकला?"], ["Who won the cricket match?"], OS, T_FA, {}, False, {}),
    ("hi", ["आज बिजली का बिल कैसे भरूं?"], ["How do I pay my electricity bill today?"], OS, T_FA, {}, False, {}),
    ("en", ["Can you help me file my income tax return?"], ["Can you help me file my income tax return?"], OS, T_FA, {}, False, {}),
]


def split_of(rid: str) -> str:
    return "dev" if int(hashlib.sha256(rid.encode()).hexdigest(), 16) % 100 < 40 else "test"


def build() -> list[EvalRow]:
    rows, counters = [], {}
    for locale, orig, eng, intent, tool, args, refuse, screen in ITEMS:
        assert len(orig) == len(eng), orig
        counters[locale] = counters.get(locale, 0) + 1
        rid = f"ag_{locale}_{counters[locale]:02d}"
        rows.append(EvalRow(id=rid, split=split_of(rid), locale=locale, turns_original=orig, turns_english=eng,
                            screen_context=screen, expected_intent=intent, expected_tool=tool,
                            expected_args=args, expected_chunk_ids=[], must_refuse=refuse))
    return rows


if __name__ == "__main__":
    out = ROOT / "eval/data/agent_eval_60.jsonl"
    rows = build()
    out.write_text("".join(r.model_dump_json() + "\n" for r in rows), "utf-8")
    print(f"wrote {len(rows)} rows -> {out}  dev={sum(r.split == 'dev' for r in rows)} test={sum(r.split == 'test' for r in rows)}")
