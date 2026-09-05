"""
Matching Engine — Greedy multi-lot matcher.
Scores lots by grade match, proximity, and price fit.
"""
from app.utils.haversine import haversine_km

# Weights for scoring
W_GRADE = 0.30
W_PROXIMITY = 0.35
W_PRICE = 0.35


def score_lot(lot, demand) -> float:
    """Score a single lot against a buyer demand. Returns 0.0-1.0."""

    # Grade match
    grade_order = {"A": 3, "B": 2, "C": 1, None: 0}
    if lot.grade == demand.desired_grade:
        grade_score = 1.0
    elif grade_order.get(lot.grade, 0) > grade_order.get(demand.desired_grade, 0):
        grade_score = 0.8  # better than required
    else:
        grade_score = 0.3  # worse than required

    # Proximity (closer = better, max 500km considered)
    if lot.lat and lot.lng and demand.lat and demand.lng:
        dist = haversine_km(lot.lat, lot.lng, demand.lat, demand.lng)
        proximity_score = max(0, 1.0 - dist / 500)
    else:
        proximity_score = 0.5  # no location data

    # Price fit (lot's mid price vs buyer's max price)
    if demand.max_price_paise_per_qtl and lot.price_mid_paise_per_qtl:
        if lot.price_mid_paise_per_qtl <= demand.max_price_paise_per_qtl:
            price_score = 1.0
        else:
            overshoot = (lot.price_mid_paise_per_qtl - demand.max_price_paise_per_qtl) \
                        / demand.max_price_paise_per_qtl
            price_score = max(0, 1.0 - overshoot)
    else:
        price_score = 0.5  # no price preference

    return W_GRADE * grade_score + W_PROXIMITY * proximity_score + W_PRICE * price_score


def match_lots_for_demand(lots: list, demand) -> list[dict]:
    """
    Greedy multi-lot matching.
    Returns list of { lot, allocated_kg, match_score } covering the demand quantity.
    """
    scored = [(lot, score_lot(lot, demand)) for lot in lots if lot.crop == demand.crop]
    scored.sort(key=lambda x: -x[1])  # highest score first

    result = []
    remaining_kg = demand.desired_qty_kg

    for lot, score in scored:
        if remaining_kg <= 0:
            break
        if lot.status != "active":
            continue
        allocated = min(lot.quantity_kg, remaining_kg)
        result.append({
            "lot": lot,
            "allocated_kg": allocated,
            "match_score": round(score, 3),
        })
        remaining_kg -= allocated

    return result


def match_demands_for_lot(demands: list, lot) -> list[dict]:
    """
    Find buyer demands matching a single lot. Returns ranked list.
    """
    scored = [(d, score_lot(lot, d)) for d in demands if d.crop == lot.crop]
    scored.sort(key=lambda x: -x[1])
    return [{"demand": d, "match_score": round(s, 3)} for d, s in scored[:10]]
