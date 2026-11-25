"""Build the RAG retrieval benchmark -> eval/data/rag_bench.jsonl  (mr / hi / en).

Every query is AUTHORED (written by hand against the corpus, NOT mined from real farmer logs, NOT
validated by native speakers yet). Expected answers are given as (source_doc, section title) and are
resolved to real `chunk_id`s by running the chunker over data/rag_corpus, so the set cannot drift
silently: if a section is renamed or removed, this script fails loudly instead of emitting a stale id.

Rows with must_refuse=True ask for things the corpus deliberately does NOT contain; they have no
expected chunks and are excluded from Hit/Recall/MRR (they are used to compare top-1 scores instead).

Split: stable hash of the id, ~40% dev / ~60% test. Tune on dev, report test.
"""
from __future__ import annotations

import hashlib
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))
from app.contracts import EvalRow  # noqa: E402
from app.rag.chunker import approx_token_counter, chunk_document, iter_corpus  # noqa: E402

CORPUS = ROOT / "data" / "rag_corpus"

# (locale, original text, english text, category, [(source_doc, section title)], must_refuse)
SF = "schemes_finance"
K, PK, PF, PL, VAL, EN, AP, MSP = (f"{SF}/{n}.md" for n in (
    "kcc", "pm_kisan", "pmfby_crop_insurance", "wdra_enwr_pledge_loan", "wdra_enwr_validity_by_crop",
    "enam_registration", "maharashtra_apmc_fees", "msp_kharif_2026_27"))
PGR, ONS, SOY = "grading/platform_grading_rules.md", "grading/wdra_onion_grade_standards.md", "grading/wdra_soyabean_grade_standards.md"
WIN, PLQ, OFR, ESC, FPO = (f"platform/{n}.md" for n in (
    "window_engine_hold_or_sell", "pledge_loan_quote", "offers_and_bargaining", "escrow_payment_flow", "fpo_pooling"))
UN, CN, MN = "glossary/units.md", "glossary/commodity_names.md", "glossary/mandi_names.md"

ITEMS = [
    # ------------------------------------------------------------------ English
    ("en", "How much interest do I pay on a Kisan Credit Card loan if I repay on time?", "How much interest do I pay on a Kisan Credit Card loan if I repay on time?", SF, [(K, "Interest rate and the prompt repayment benefit")], False),
    ("en", "What is the collateral free limit for KCC?", "What is the collateral free limit for KCC?", SF, [(K, "What the KCC is")], False),
    ("en", "Is the KCC subvention limit 3 lakh or 5 lakh?", "Is the KCC subvention limit 3 lakh or 5 lakh?", SF, [(K, "Which loan limit qualifies for the subvention: sources differ")], False),
    ("en", "How many instalments of PM-KISAN do I get in a year?", "How many instalments of PM-KISAN do I get in a year?", SF, [(PK, "What farmers receive")], False),
    ("en", "How do I complete e-KYC for PM-KISAN?", "How do I complete e-KYC for PM-KISAN?", SF, [(PK, "e-KYC is compulsory")], False),
    ("en", "Which documents are needed for PM-KISAN?", "Which documents are needed for PM-KISAN?", SF, [(PK, "Documents needed")], False),
    ("en", "How much premium does a farmer pay under PMFBY for kharif crops?", "How much premium does a farmer pay under PMFBY for kharif crops?", SF, [(PF, "What a farmer pays")], False),
    ("en", "What is the last date to enrol for crop insurance?", "What is the last date to enrol for crop insurance?", SF, [(PF, "Enrolment and cut-off dates")], False),
    ("en", "Can I get a loan against my stored onion?", "Can I get a loan against my stored onion?", SF, [(PL, "Perishable produce"), (VAL, "Fresh onion")], False),
    ("en", "How long is an e-NWR valid for soyabean?", "How long is an e-NWR valid for soyabean?", SF, [(VAL, "Soyabean")], False),
    ("en", "What is the credit guarantee scheme for warehouse receipt loans?", "What is the credit guarantee scheme for warehouse receipt loans?", SF, [(PL, "Credit guarantee scheme")], False),
    ("en", "How do I register as a farmer on e-NAM?", "How do I register as a farmer on e-NAM?", SF, [(EN, "How a farmer registers")], False),
    ("en", "Who pays the APMC market fee, the farmer or the buyer?", "Who pays the APMC market fee, the farmer or the buyer?", SF, [(AP, "Market fee")], False),
    ("en", "What is the MSP of soyabean this kharif season?", "What is the MSP of soyabean this kharif season?", SF, [(MSP, "Soyabean and tur")], False),
    ("en", "Does onion have a minimum support price?", "Does onion have a minimum support price?", SF, [(MSP, "Onion has no MSP")], False),
    ("en", "What moisture is allowed for Grade I soyabean?", "What moisture is allowed for Grade I soyabean?", "grading", [(SOY, "Grade-I, Grade-II and Grade-III")], False),
    ("en", "What size classes does WDRA define for onion bulbs?", "What size classes does WDRA define for onion bulbs?", "grading", [(ONS, "Size")], False),
    ("en", "How does the platform decide Grade A for wheat?", "How does the platform decide Grade A for wheat?", "grading", [(PGR, "Soyabean, wheat, gram, maize and other grains and oilseeds")], False),
    ("en", "Why did the app refuse to give me hold or sell advice?", "Why did the app refuse to give me hold or sell advice?", "platform", [(WIN, "When the engine refuses (NO_ADVICE)")], False),
    ("en", "How many times can we counter an offer?", "How many times can we counter an offer?", "platform", [(OFR, "Three rounds only")], False),
    ("en", "When does the buyer's money get released to the farmer?", "When does the buyer's money get released to the farmer?", "platform", [(ESC, "The steps")], False),
    ("en", "How is the grade of a pooled FPO batch decided?", "How is the grade of a pooled FPO batch decided?", "platform", [(FPO, "Rules")], False),
    ("en", "How many kg is one bori?", "How many kg is one bori?", "glossary", [(UN, "bori")], False),
    ("en", "What are the official WDRA grade limits for whole tur?", "What are the official WDRA grade limits for whole tur?", None, [], True),
    ("en", "On which date will the next PM-KISAN instalment come?", "On which date will the next PM-KISAN instalment come?", None, [], True),
    # ------------------------------------------------------------------ Marathi
    ("mr", "किसान क्रेडिट कार्डवर वेळेवर परतफेड केल्यास व्याज किती लागते?", "How much interest is charged on a Kisan Credit Card if I repay on time?", SF, [(K, "Interest rate and the prompt repayment benefit")], False),
    ("mr", "केसीसी म्हणजे काय आणि तारणाशिवाय किती कर्ज मिळते?", "What is KCC and how much loan is available without collateral?", SF, [(K, "What the KCC is")], False),
    ("mr", "पीएम किसानचा हप्ता वर्षातून किती वेळा येतो?", "How many times a year does the PM-KISAN instalment come?", SF, [(PK, "What farmers receive")], False),
    ("mr", "पीएम किसानसाठी ई-केवायसी कशी करायची?", "How do I do e-KYC for PM-KISAN?", SF, [(PK, "e-KYC is compulsory")], False),
    ("mr", "पीएम किसानसाठी कोणती कागदपत्रे लागतात?", "Which documents are needed for PM-KISAN?", SF, [(PK, "Documents needed")], False),
    ("mr", "पीक विमा योजनेत शेतकऱ्याला किती हप्ता भरावा लागतो?", "How much premium does a farmer pay in the crop insurance scheme?", SF, [(PF, "What a farmer pays")], False),
    ("mr", "पीक विम्यासाठी नोंदणीची शेवटची तारीख कोणती?", "What is the last date to register for crop insurance?", SF, [(PF, "Enrolment and cut-off dates")], False),
    ("mr", "गोदामात ठेवलेल्या मालावर कर्ज कसे मिळते?", "How do I get a loan on produce kept in a warehouse?", SF, [(PL, "How it works"), (PL, "Loan terms")], False),
    ("mr", "सोयाबीनची गोदाम पावती किती दिवस चालते?", "For how many days is the warehouse receipt for soybean valid?", SF, [(VAL, "Soyabean")], False),
    ("mr", "ई-नाममध्ये शेतकरी म्हणून नोंदणी कशी करावी?", "How do I register as a farmer on e-NAM?", SF, [(EN, "How a farmer registers")], False),
    ("mr", "बाजार समितीचे शुल्क कोण भरते?", "Who pays the market committee fee?", SF, [(AP, "Market fee")], False),
    ("mr", "सोयाबीनचा हमीभाव किती आहे?", "What is the minimum support price of soybean?", SF, [(MSP, "Soyabean and tur")], False),
    ("mr", "कांद्याला हमीभाव मिळतो का?", "Does onion get a minimum support price?", SF, [(MSP, "Onion has no MSP")], False),
    ("mr", "सोयाबीनमध्ये ओलावा किती चालतो?", "How much moisture is allowed in soybean?", "grading", [(SOY, "Grade-I, Grade-II and Grade-III")], False),
    ("mr", "कांद्याचा आकार कसा मोजतात?", "How is the size of an onion measured?", "grading", [(ONS, "Size")], False),
    ("mr", "टोमॅटोची ग्रेड कशी ठरते?", "How is the grade of tomato decided?", "grading", [(PGR, "Tomato, potato, green chilli and banana")], False),
    ("mr", "ॲपने मला विकू की थांबू याचा सल्ला का दिला नाही?", "Why did the app not tell me whether to sell or wait?", "platform", [(WIN, "When the engine refuses (NO_ADVICE)")], False),
    ("mr", "भाव पाडून मागितला तर किती वेळा वाटाघाटी करता येते?", "If the buyer asks for a lower price, how many rounds of bargaining are allowed?", "platform", [(OFR, "Three rounds only")], False),
    ("mr", "खरेदीदाराचे पैसे शेतकऱ्याला कधी मिळतात?", "When does the farmer get the buyer's money?", "platform", [(ESC, "The steps")], False),
    ("mr", "एफपीओ मध्ये लहान शेतकऱ्यांचा माल एकत्र कसा विकतात?", "How does an FPO sell small farmers' produce together?", "platform", [(FPO, "What pooling does"), (FPO, "Rules")], False),
    ("mr", "एका बोरीत किती किलो असतात?", "How many kilograms are in one bori?", "glossary", [(UN, "bori")], False),
    ("mr", "शेतकरी कर्जमाफी कधी मिळेल?", "When will the farm loan waiver come?", None, [], True),
    ("mr", "जीएसटी रिटर्न कसा भरायचा?", "How do I file a GST return?", None, [], True),
    # ------------------------------------------------------------------ Hindi
    ("hi", "किसान क्रेडिट कार्ड पर समय पर चुकाने से कितना ब्याज लगता है?", "How much interest applies on a Kisan Credit Card if repaid on time?", SF, [(K, "Interest rate and the prompt repayment benefit")], False),
    ("hi", "केसीसी में बिना गारंटी कितना कर्ज मिलता है?", "How much loan does KCC give without collateral?", SF, [(K, "What the KCC is")], False),
    ("hi", "पीएम किसान की किस्त साल में कितनी बार आती है?", "How many times a year does the PM-KISAN instalment come?", SF, [(PK, "What farmers receive")], False),
    ("hi", "पीएम किसान में ई-केवाईसी कैसे करें?", "How do I do e-KYC in PM-KISAN?", SF, [(PK, "e-KYC is compulsory")], False),
    ("hi", "पीएम किसान के लिए कौन से कागज चाहिए?", "Which papers are needed for PM-KISAN?", SF, [(PK, "Documents needed")], False),
    ("hi", "फसल बीमा में किसान को कितना प्रीमियम देना पड़ता है?", "How much premium does a farmer pay in crop insurance?", SF, [(PF, "What a farmer pays")], False),
    ("hi", "फसल बीमा कराने की आखिरी तारीख क्या है?", "What is the last date to get crop insurance?", SF, [(PF, "Enrolment and cut-off dates")], False),
    ("hi", "गोदाम में रखी फसल पर लोन कैसे मिलेगा?", "How can I get a loan on crop kept in a warehouse?", SF, [(PL, "How it works"), (PL, "Loan terms")], False),
    ("hi", "प्याज की गोदाम रसीद कितने दिन चलती है?", "For how many days is the warehouse receipt for onion valid?", SF, [(VAL, "Fresh onion")], False),
    ("hi", "ई-नाम पर किसान के रूप में रजिस्ट्रेशन कैसे करें?", "How do I register as a farmer on e-NAM?", SF, [(EN, "How a farmer registers")], False),
    ("hi", "मंडी शुल्क कौन देता है, किसान या खरीदार?", "Who pays the mandi fee, farmer or buyer?", SF, [(AP, "Market fee")], False),
    ("hi", "सोयाबीन का एमएसपी कितना है?", "What is the MSP of soybean?", SF, [(MSP, "Soyabean and tur")], False),
    ("hi", "क्या प्याज पर न्यूनतम समर्थन मूल्य मिलता है?", "Is a minimum support price given on onion?", SF, [(MSP, "Onion has no MSP")], False),
    ("hi", "सोयाबीन में नमी कितनी चलती है?", "How much moisture is acceptable in soybean?", "grading", [(SOY, "Grade-I, Grade-II and Grade-III")], False),
    ("hi", "प्याज के आकार की श्रेणियाँ क्या हैं?", "What are the size categories for onion?", "grading", [(ONS, "Size")], False),
    ("hi", "प्लेटफॉर्म पर गेहूं का ग्रेड ए कैसे तय होता है?", "How is Grade A wheat decided on the platform?", "grading", [(PGR, "Soyabean, wheat, gram, maize and other grains and oilseeds")], False),
    ("hi", "ऐप ने मुझे बेचने या रुकने की सलाह क्यों नहीं दी?", "Why did the app not advise me to sell or hold?", "platform", [(WIN, "When the engine refuses (NO_ADVICE)")], False),
    ("hi", "मोलभाव के कितने राउंड हो सकते हैं?", "How many rounds of bargaining are allowed?", "platform", [(OFR, "Three rounds only")], False),
    ("hi", "खरीदार का पैसा किसान को कब मिलता है?", "When does the farmer receive the buyer's money?", "platform", [(ESC, "The steps")], False),
    ("hi", "एफपीओ छोटे किसानों का माल मिलाकर कैसे बेचता है?", "How does an FPO combine small farmers' produce and sell it?", "platform", [(FPO, "What pooling does"), (FPO, "Rules")], False),
    ("hi", "एक बोरी में कितने किलो होते हैं?", "How many kilograms are in one bori?", "glossary", [(UN, "bori")], False),
    ("hi", "टमाटर के लिए WDRA के आधिकारिक ग्रेड नियम क्या हैं?", "What are the official WDRA grade rules for tomato?", None, [], True),
    ("hi", "इस महीने बिजली का बिल कैसे माफ होगा?", "How will my electricity bill be waived this month?", None, [], True),
    # ------------------------------------------------------------------ glossary extras (appended)
    ("en", "What is the weight of one goni?", "What is the weight of one goni?", "glossary", [(UN, "goni")], False),
    ("en", "What is tur called in Hindi and Marathi?", "What is tur called in Hindi and Marathi?", "glossary", [(CN, "tur")], False),
    ("mr", "खंडी म्हणजे किती किलो?", "How many kilograms is a khandi?", "glossary", [(UN, "khandi")], False),
    ("mr", "तूर म्हणजे इंग्रजीत काय?", "What is tur in English?", "glossary", [(CN, "tur")], False),
    ("hi", "एक क्विंटल में कितने किलो होते हैं?", "How many kilograms are in one quintal?", "glossary", [(UN, "quintal")], False),
    ("hi", "लासलगांव मंडी को और किस नाम से लिखते हैं?", "By what other names is Lasalgaon mandi written?", "glossary", [(MN, "lasalgaon")], False),
]


def split_of(rid: str) -> str:
    return "dev" if int(hashlib.sha256(rid.encode()).hexdigest(), 16) % 100 < 40 else "test"


def chunk_index() -> dict[tuple[str, str], list[str]]:
    """(source_doc, last heading in the section path) -> chunk_ids (a long section can span several)."""
    idx: dict[tuple[str, str], list[str]] = {}
    for rel, raw in iter_corpus(CORPUS):
        for c in chunk_document(rel, raw, approx_token_counter):
            idx.setdefault((c.source_doc, c.section_title.split(" > ")[-1]), []).append(c.chunk_id)
    return idx


def build() -> list[EvalRow]:
    idx = chunk_index()
    rows: list[EvalRow] = []
    counters: dict[str, int] = {}
    for locale, orig, eng, cat, expected, refuse in ITEMS:
        counters[locale] = counters.get(locale, 0) + 1
        rid = f"rag_{locale}_{counters[locale]:02d}"
        ids: list[str] = []
        for doc, title in expected:
            if (doc, title) not in idx:
                raise SystemExit(f"{rid}: no chunk for section {title!r} in {doc} (renamed or removed?)")
            ids += idx[(doc, title)]
        args = {"category": cat} if cat else {}
        rows.append(EvalRow(
            id=rid, split=split_of(rid), locale=locale, turns_original=[orig], turns_english=[eng],
            expected_intent="RAG", expected_tool="search_agri_knowledge", expected_args=args,
            expected_chunk_ids=ids, must_refuse=refuse))
    return rows


if __name__ == "__main__":
    out = ROOT / "eval/data/rag_bench.jsonl"
    rows = build()
    out.write_text("".join(r.model_dump_json() + "\n" for r in rows), "utf-8")
    ans = [r for r in rows if not r.must_refuse]
    print(f"wrote {len(rows)} rows ({len(ans)} answerable, {len(rows) - len(ans)} must_refuse) -> {out}  "
          f"dev={sum(r.split == 'dev' for r in rows)} test={sum(r.split == 'test' for r in rows)}")
