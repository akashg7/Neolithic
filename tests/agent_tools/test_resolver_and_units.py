import pytest

from app.agents.tools.units import rupees_to_paise, to_kg
from app.utils.id_resolver import ResolveError, normalize, slug_for


@pytest.mark.parametrize("ref,expected", [
    ("cmd_onion", "Onion"), ("1", "Onion"), (1, "Onion"), ("Onion", "Onion"),
    ("कांदा", "Onion"), ("kanda", "Onion"), ("pyaz", "Onion"), ("प्याज", "Onion"),
    ("cmd_soyabean", "Soyabean"), ("soybean", "Soyabean"), ("सोयाबिन", "Soyabean"),
    ("cmd_gram", "Bengal Gram"), ("chana", "Bengal Gram"), ("हरभरा", "Bengal Gram"),
    ("Tomatto", "Tomato"),  # fuzzy (a swapped-letter "Onoin" is deliberately below the cutoff)
])
def test_resolve_commodity(catalog, ref, expected):
    assert catalog.resolve("commodity", ref).name == expected


@pytest.mark.parametrize("ref,expected", [
    ("mkt_lasalgaon", "Lasalgaon APMC"), ("Lasalgaon", "Lasalgaon APMC"),
    ("लासलगाव", "Lasalgaon APMC"), ("लासलगाव कृषी उत्पन्न बाजार समिती", "Lasalgaon APMC"),
    ("Lasalgon", "Lasalgaon APMC"),            # fuzzy
    ("mkt_pune", "Pune APMC"),                 # exact beats the Moshi prefix match
    ("moshi", "Pune(Moshi) APMC"),
    ("mkt_ahmednagar", "Ahilyanagar APMC"), ("ahmednagar", "Ahilyanagar APMC"),
    ("2", "Nashik APMC"),
])
def test_resolve_market(catalog, ref, expected):
    assert catalog.resolve("market", ref).name == expected


@pytest.mark.parametrize("ref,expected", [
    ("dist_nashik", "Nashik"), ("नाशिक", "Nashik"),
    ("dist_aurangabad", "Chhatrapati Sambhajinagar"), ("aurangabad", "Chhatrapati Sambhajinagar"),
    ("dist_ahmednagar", "Ahmednagar"),
])
def test_resolve_district(catalog, ref, expected):
    assert catalog.resolve("district", ref).name == expected


def test_unknown_is_not_found_not_a_default(catalog):
    with pytest.raises(ResolveError) as exc:
        catalog.resolve("commodity", "dragonfruit")
    assert not exc.value.ambiguous


def test_unknown_numeric_id(catalog):
    with pytest.raises(ResolveError):
        catalog.resolve("market", "999")


def test_ambiguous_returns_candidates(catalog):
    with pytest.raises(ResolveError) as exc:
        catalog.resolve("market", "pimpal")
    assert exc.value.ambiguous
    assert {c.name for c in exc.value.candidates} == {"Pimpalgaon APMC", "Pimpalner APMC"}


def test_slugs_match_the_app():
    assert slug_for("commodity", "Onion") == "cmd_onion"
    assert slug_for("commodity", "Soyabean") == "cmd_soyabean"
    assert slug_for("commodity", "Bengal Gram") == "cmd_gram"
    assert slug_for("market", "Lasalgaon APMC") == "mkt_lasalgaon"
    assert slug_for("market", "Ahilyanagar APMC") == "mkt_ahmednagar"
    assert slug_for("district", "Nashik") == "dist_nashik"
    assert slug_for("district", "Chhatrapati Sambhajinagar") == "dist_aurangabad"


def test_normalize_devanagari_and_noise():
    assert normalize("Lasalgaon APMC") == normalize("mkt_lasalgaon") == "lasalgaon"
    assert normalize("लासलगाव बाजार समिती") == normalize("लासलगाव")


@pytest.mark.parametrize("qty,unit,kg", [
    (20, "bori", 1000), (20, "बोरी", 1000), (10, "goni", 500), (4.5, "quintal", 450),
    (4, "क्विंटल", 400), (2, "ton", 2000), (750, "kg", 750),
])
def test_units(qty, unit, kg):
    assert to_kg(qty, unit) == kg


def test_units_reject_unknown_and_nonpositive():
    with pytest.raises(ValueError):
        to_kg(3, "khandi")
    with pytest.raises(ValueError):
        to_kg(0, "kg")


def test_rupees_to_paise():
    assert rupees_to_paise(2200) == 220000
    assert rupees_to_paise(1950.5) == 195050
