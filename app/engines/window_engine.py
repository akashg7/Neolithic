"""
Window + Refusal Engine — Computes SELL/HOLD/NO_ADVICE recommendation.
Uses price forecasts to calculate expected gain vs. holding costs.
"""
from app.engines.price_engine import price_engine

# Configurable thresholds
BAND_WIDTH_THRESHOLD = 0.25  # 25%
TRANSPORT_COST_PAISE_PER_KM = 50
COMMISSION_RATE = 0.025  # 2.5%
STORAGE_COST_PAISE_PER_KG_PER_DAY = 5
SPOILAGE_RATE_PER_DAY = 0.002  # 0.2%


def compute_sale_window(
    crop: str,
    mandi: str,
    quantity_kg: int,
    current_price_mid_paise: int,
    distance_km: float,
) -> dict:
    """
    Algorithm:
    1. Pull p10/p50/p90 for next 14 days
    2. Compute band_width = (p90 - p10) / p50
    3. If band_width > BAND_WIDTH_THRESHOLD:
         return NO_ADVICE + reason
    4. Else:
         For each future day:
           expected_gain = (p50_future - current_mid) × quantity
                         - transport_cost - commission - storage_cost - spoilage
           worst_case = (p10_future - current_mid) × quantity - same costs
         Find the day with max expected_gain where worst_case > 0
         Return HOLD (with that date) or SELL (if today is best)
    """
    forecasts = price_engine.predict_range(mandi, crop, days=14)

    # Check band width on the nearest forecast
    latest = forecasts[0]
    band_width = (latest["p90_paise"] - latest["p10_paise"]) / latest["p50_paise"]

    if band_width > BAND_WIDTH_THRESHOLD:
        return {
            "recommendation": "NO_ADVICE",
            "reason": f"Forecast too uncertain for {crop} at {mandi} "
                      f"(band width {band_width:.0%}, threshold {BAND_WIDTH_THRESHOLD:.0%})"
        }

    best_day = None
    best_gain = 0
    best_worst = 0
    best_costs = {}

    for i, fc in enumerate(forecasts):
        days_from_now = i + 1
        transport = int(distance_km * TRANSPORT_COST_PAISE_PER_KM)
        commission = int(fc["p50_paise"] * quantity_kg / 100 * COMMISSION_RATE)
        storage = int(STORAGE_COST_PAISE_PER_KG_PER_DAY * quantity_kg * days_from_now)
        spoilage = int(current_price_mid_paise * quantity_kg / 100
                       * SPOILAGE_RATE_PER_DAY * days_from_now)
        total_costs = transport + commission + storage + spoilage

        gain = (fc["p50_paise"] - current_price_mid_paise) * quantity_kg // 100 - total_costs
        worst = (fc["p10_paise"] - current_price_mid_paise) * quantity_kg // 100 - total_costs

        if gain > best_gain and worst > -total_costs:
            best_day = i
            best_gain = gain
            best_worst = worst
            best_costs = {
                "transport_paise": transport,
                "commission_paise": commission,
                "storage_paise": storage,
                "spoilage_estimate_paise": spoilage,
            }

    if best_day is None or best_day == 0:
        return {
            "recommendation": "SELL",
            "expected_gain_paise": 0,
            "worst_case_paise": 0,
            "itemised_costs": {},
        }

    return {
        "recommendation": "HOLD",
        "expected_gain_paise": best_gain,
        "worst_case_paise": best_worst,
        "hold_days": best_day + 1,
        "itemised_costs": best_costs,
    }
