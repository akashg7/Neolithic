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


def match_lots_for_demand(lots: list, demand) -> dict:
    """
    Greedy multi-lot matching.
    Returns { "matches": [ MatchRow ] }
    """
    scored = [(lot, score_lot(lot, demand)) for lot in lots if lot.commodity_id == demand.commodity_id]
    scored.sort(key=lambda x: -x[1])  # highest score first

    if not scored:
        return {"matches": []}

    # Generate a single-lot match if best lot fills demand
    best_lot, best_score = scored[0]
    matches = []
    
    if best_lot.qty_kg >= demand.qty_kg:
        matches.append({
            "kind": "SINGLE",
            "lots": [{"lot_id": str(best_lot.id), "qty_allocated_kg": demand.qty_kg}],
            "total_qty_kg": demand.qty_kg,
            "fill_bps": 10000,
            "avg_score": 850, # mock
            "grade": best_lot.grade if best_lot.grade in ['A','B','C'] else 'B',
            "distance_km": 45,
            "score": round(best_score, 3),
            "why_mr": "जवळचे अंतर, पूर्ण ऑर्डर एकाच शेतकर्‍याकडून.",
            "why_en": "Close distance, fills full order from single farmer."
        })
    else:
        # Generate combination match
        combo_lots = []
        combo_qty = 0
        sum_score = 0
        for lot, score in scored:
            if lot.status != "LISTED":
                continue
            alloc = min(lot.qty_kg, demand.qty_kg - combo_qty)
            combo_lots.append({"lot_id": str(lot.id), "qty_allocated_kg": alloc})
            combo_qty += alloc
            sum_score += score
            if combo_qty >= demand.qty_kg:
                break
                
        if combo_lots:
            fill_bps = int((combo_qty / demand.qty_kg) * 10000) if demand.qty_kg > 0 else 0
            matches.append({
                "kind": "COMBINATION",
                "lots": combo_lots,
                "total_qty_kg": combo_qty,
                "fill_bps": fill_bps,
                "avg_score": 800, # mock
                "grade": 'B',
                "distance_km": 50,
                "score": round(sum_score / len(combo_lots), 3),
                "why_mr": f"ऑर्डर पूर्ण करण्यासाठी {len(combo_lots)} शेतकर्‍यांची एकत्र खरेदी.",
                "why_en": f"Fills the order using {len(combo_lots)} farmers."
            })

    return {"matches": matches}


def match_demands_for_lot(demands: list, lot) -> dict:
    """
    Find buyer demands matching a single lot. Returns MatchesRes format.
    """
    scored = [(d, score_lot(lot, d)) for d in demands if d.commodity_id == lot.commodity_id]
    scored.sort(key=lambda x: -x[1])
    
    matches = []
    for d, s in scored[:10]:
        alloc = min(lot.qty_kg, d.qty_kg)
        fill_bps = int((alloc / d.qty_kg) * 10000) if d.qty_kg > 0 else 0
        matches.append({
            "kind": "SINGLE",
            "lots": [{"lot_id": str(lot.id), "qty_allocated_kg": alloc}],
            "total_qty_kg": alloc,
            "fill_bps": fill_bps,
            "avg_score": 850,
            "grade": lot.grade if lot.grade in ['A','B','C'] else 'B',
            "distance_km": 45,
            "score": round(s, 3),
            "why_mr": "उत्तम जुळणी.",
            "why_en": "Good match."
        })
        
    return {"matches": matches}
