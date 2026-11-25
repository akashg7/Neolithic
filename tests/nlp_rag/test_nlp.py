import pytest

from app.nlp.hints import extract_hints
from app.nlp.lexicon import (
    Lexicon,
    commodity_candidates,
    mandi_candidates,
    resolve_commodity,
    resolve_mandi,
    scan_names,
)
from app.nlp.normalize import fold, normalize_text
from app.nlp.units import UnknownUnitError, canonical_unit, parse_quantities, to_kg


# ---------------------------------------------------------------- normalizer
def test_digits_danda_whitespace():
    assert normalize_text("  २०   बोरी ।  कांदा ") == "20 बोरी . कांदा"


def test_zero_width_and_nfkc():
    assert normalize_text("ｋｇ‍") == "kg"


def test_empty():
    assert normalize_text("") == ""
    assert normalize_text(None) == ""


def test_fold_unifies_spellings():
    assert fold("कांदा") == fold("काँदा") == fold("कादा")
    assert fold("बोऱ्या") == fold("बोर्या")


# ---------------------------------------------------------------- to_kg
@pytest.mark.parametrize(
    "value,unit,kg",
    [
        (1, "bori", 50), (20, "bori", 1000), (20, "बोरी", 1000), (2, "quintal", 200),
        (2, "क्विंटल", 200), (1, "ton", 1000), (3, "टन", 3000), (5, "kg", 5),
        (5, "किलो", 5), (0.5, "bori", 25), (1.25, "quintal", 125), (1.5, "QUINTAL", 150),
    ],
)
def test_to_kg_known_units(value, unit, kg):
    assert to_kg(value, unit) == kg


def test_to_kg_rounds_half_up():
    assert to_kg(1.25, "bori") == 63  # 62.5


@pytest.mark.parametrize("unit", ["khandi", "खंडी", "goni", "maund"])
def test_to_kg_variable_units_raise(unit):
    with pytest.raises(UnknownUnitError) as e:
        to_kg(2, unit)
    assert e.value.reason == "variable_size"


def test_to_kg_unknown_unit_raises():
    with pytest.raises(UnknownUnitError) as e:
        to_kg(2, "furlong")
    assert e.value.reason == "unknown"


@pytest.mark.parametrize("v", [0, -1, None])
def test_to_kg_bad_quantity(v):
    with pytest.raises(ValueError):
        to_kg(v, "kg")


def test_canonical_unit_aliases():
    assert canonical_unit("Bags") == "bori"
    assert canonical_unit("qtl") == "quintal"


# ---------------------------------------------------------------- parse_quantities
@pytest.mark.parametrize(
    "text,kg",
    [
        ("२० बोरी कांदा", 1000),
        ("20 bori", 1000),
        ("20bori", 1000),
        ("२०बोऱ्या", 1000),
        ("दोन क्विंटल", 200),
        ("दो क्विंटल", 200),
        ("two quintals", 200),
        ("1,000 kg", 1000),
        ("1000 किलो", 1000),
        ("साडे तीन टन", 3500),
        ("साडेतीन टन", 3500),
        ("साढ़े तीन टन", 3500),
        ("दीड क्विंटल", 150),
        ("डेढ़ क्विंटल", 150),
        ("अडीच क्विंटल", 250),
        ("ढाई क्विंटल", 250),
        ("सव्वा क्विंटल", 125),
        ("पाच हजार किलो", 5000),
        ("दो सौ पचास किलो", 250),
        ("दोनशे किलो", 200),
        ("पंचवीस बोरी", 1250),
        ("5 हजार किलो", 5000),
        ("क्विंटलचा भाव २ क्विंटलचा", 200),
        ("I have 5000kg of onion", 5000),
        ("twenty bags", 1000),
    ],
)
def test_parse_quantity_kg(text, kg):
    q = parse_quantities(text)
    assert q, text
    assert q[0].kg == kg


def test_parse_no_unit_no_quantity():
    assert parse_quantities("मला कांदा विकायचा आहे") == []
    assert parse_quantities("price of onion today") == []
    assert parse_quantities("I want to sell 20 onions") == []


def test_parse_multiple():
    q = parse_quantities("2 quintal onion and 5 bori potato")
    assert [x.kg for x in q] == [200, 250]


def test_parse_variable_unit_has_no_kg():
    q = parse_quantities("10 खंडी")
    assert q[0].unit == "khandi" and q[0].kg is None


# ---------------------------------------------------------------- lexicon
@pytest.mark.parametrize(
    "name,cid",
    [
        ("कांदा", "cmd_onion"), ("काँदा", "cmd_onion"), ("kanda", "cmd_onion"),
        ("ONION", "cmd_onion"), ("प्याज़", "cmd_onion"), ("pyaz", "cmd_onion"),
        ("tamatr", "cmd_tomato"), ("टमाटर", "cmd_tomato"), ("गहू", "cmd_wheat"),
        ("soyabeen", "cmd_soybean"), ("कापूस", "cmd_cotton"), ("डाळिंब", "cmd_pomegranate"),
    ],
)
def test_resolve_commodity(name, cid):
    assert resolve_commodity(name) == cid


@pytest.mark.parametrize(
    "name,mid",
    [
        ("लासलगाव", "mkt_lasalgaon"), ("Lasalgaon", "mkt_lasalgaon"),
        ("lasalgaon market", "mkt_lasalgaon"), ("लासलगाव मंडी", "mkt_lasalgaon"),
        ("nasik", "mkt_nashik"), ("नासिक", "mkt_nashik"), ("Aurangabad", "mkt_chh_sambhajinagar"),
        ("पुणे", "mkt_pune"),
    ],
)
def test_resolve_mandi(name, mid):
    assert resolve_mandi(name) == mid


@pytest.mark.parametrize("name", ["zzz", "", "   ", "xyzabc", "हेलिकॉप्टर"])
def test_below_cutoff_returns_none(name):
    assert resolve_commodity(name) is None
    assert resolve_mandi(name) is None


def test_candidates_unknown_is_empty_and_resolved_is_single():
    assert commodity_candidates("zzz") == []
    assert commodity_candidates("onion") == ["cmd_onion"]
    assert mandi_candidates("lasalgaon") == ["mkt_lasalgaon"]


def test_ambiguous_name_returns_none_but_lists_candidates():
    lex = Lexicon(
        {
            "commodities": {},
            "mandis": {
                "mkt_pimpalgaon_a": {"aliases": ["pimpalgaon"], "stems": []},
                "mkt_pimpalgaon_b": {"aliases": ["pimpalgaon"], "stems": []},
            },
        }
    )
    assert lex.resolve("mandi", "pimpalgaon") is None
    assert lex.candidates("mandi", "pimpalgaon") == ["mkt_pimpalgaon_a", "mkt_pimpalgaon_b"]


def test_inflected_forms_via_stems():
    kinds = {(m.kind, m.id) for m in scan_names("कांद्याचा भाव लासलगावला किती आहे")}
    assert kinds == {("commodity", "cmd_onion"), ("mandi", "mkt_lasalgaon")}
    assert {m.id for m in scan_names("गव्हाला काय भाव")} == {"cmd_wheat"}


def test_scan_no_false_positives_in_plain_english():
    assert scan_names("tell us the weather forecast for tomorrow, I will sell later") == []
    assert scan_names("What is my bid price") == []


def test_scan_multiword_names():
    assert {m.id for m in scan_names("sell at pimpalgaon baswant")} == {"mkt_pimpalgaon"}
    assert {m.id for m in scan_names("छत्रपती संभाजीनगर बाजार")} == {"mkt_chh_sambhajinagar"}


# ---------------------------------------------------------------- hints
def test_hints_marathi_full():
    h = extract_hints("माझा २० बोरी कांदा लासलगावला विकायचा आहे")
    assert h == {"quantity_kg": 1000, "commodity": "cmd_onion", "mandi": "mkt_lasalgaon"}


def test_hints_hindi_full():
    h = extract_hints("मुझे 5 क्विंटल प्याज़ नासिक मंडी में बेचना है")
    assert h == {"quantity_kg": 500, "commodity": "cmd_onion", "mandi": "mkt_nashik"}


def test_hints_english_full():
    h = extract_hints("Price of onion at Lasalgaon for 1000 kg")
    assert h == {"quantity_kg": 1000, "commodity": "cmd_onion", "mandi": "mkt_lasalgaon"}


def test_hints_unknown_unit_is_flagged_not_guessed():
    h = extract_hints("मला १० खंडी कापूस विकायचा")
    assert h == {"unit_unknown": "khandi", "commodity": "cmd_cotton"}
    assert "quantity_kg" not in h


def test_hints_multiple_commodities_are_candidates():
    h = extract_hints("onion and tomato price")
    assert "commodity" not in h
    assert h["commodity_candidates"] == ["cmd_onion", "cmd_tomato"]


def test_hints_multiple_quantities():
    h = extract_hints("2 quintal onion and 5 bori onion")
    assert "quantity_kg" not in h and len(h["quantities"]) == 2


def test_hints_same_quantity_twice_is_one_hint():
    assert extract_hints("1000 kg or 20 bori")["quantity_kg"] == 1000


def test_hints_empty_for_chitchat():
    assert extract_hints("नमस्कार") == {}
    assert extract_hints("hello") == {}


# hints override the model, so everyday words must not trigger a commodity/mandi hint
@pytest.mark.parametrize(
    "text",
    [
        "माझ्या ऑफरचे पैसे एस्क्रोमध्ये आले का?",   # आले = 'came'
        "मी अर्ज केला आहे",                          # केला = 'did'
        "ते मंडीत आले आणि भाव विचारला",
        "मला शेंगा आवडतात",
    ],
)
def test_everyday_words_do_not_make_hints(text):
    h = extract_hints(text)
    assert "commodity" not in h and "commodity_candidates" not in h, h
