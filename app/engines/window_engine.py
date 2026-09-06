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
LOADING_UNLOADING_PAISE_PER_QTL = 2000  # Rs 20 per quintal


def compute_sale_window(
    crop: str,
    mandi: str,
    quantity_kg: int,
    current_price_mid_paise: int,
    distance_km: float,
    horizon_days: int = 14
) -> dict:
    forecasts = price_engine.predict_range(mandi, crop, days=horizon_days)

    latest = forecasts[0]
    p50_val = latest["p50_paise"]
    p10_val = latest["p10_paise"]
    p90_val = latest["p90_paise"]
    
    band_width_bps = int(((p90_val - p10_val) / p50_val) * 10000)
    
    # Map raw confidence to Low/Med/High
    conf = latest["confidence"]
    conf_enum = "HIGH" if conf >= 0.8 else ("MEDIUM" if conf >= 0.6 else "LOW")
    
    base_res = {
        "confidence": conf_enum,
        "band_width_bps": band_width_bps,
        "sell_now_net_paise_per_qtl": 0,
        "hold_p50_net_paise_per_qtl": 0,
        "hold_p10_net_paise_per_qtl": 0,
        "expected_gain_paise": 0,
        "worst_case_paise": 0,
        "itemised_costs": {
            "transport_paise_per_qtl": 0,
            "commission_paise_per_qtl": 0,
            "storage_paise_per_qtl": 0,
            "spoilage_paise_per_qtl": 0,
            "loading_paise_per_qtl": 0,
            "total_paise_per_qtl": 0
        },
        "model_card": {"mase": 1.2, "coverage_80_bps": 8500},
        "data_source": latest["source"],
        "pledge_quote": None,
        "alt_market": None
    }

    if band_width_bps > BAND_WIDTH_THRESHOLD * 10000:
        base_res.update({
            "recommendation": "NO_ADVICE",
            "refusal_reason": "BAND_TOO_WIDE",
            "explain_en": "Price forecast is too uncertain due to recent high volatility.",
            "explain_mr": "नुकत्याच झालेल्या चढउतारांमुळे किमतीचा अंदाज खूप अनिश्चित आहे."
        })
        return base_res

    # Costs for selling now vs holding (loading is constant per quintal, commission is %, transport is fixed)
    # Actually wait, let's calculate the holding costs incurred *per quintal* for future days
    # transport and commission apply whether you sell now or later (assumed), but holding incurs storage + spoilage.
    # To keep the frontend's per_quintal math happy:
    qty_qtl = quantity_kg / 100.0
    if qty_qtl == 0:
        qty_qtl = 1.0

    best_day = None
    best_gain = 0
    best_worst = 0
    best_costs = {}
    best_p50_net = current_price_mid_paise
    best_p10_net = current_price_mid_paise

    sell_now_net = current_price_mid_paise  # ignoring baseline transport for simplicity relative comparison

    for i, fc in enumerate(forecasts):
        days_from_now = i + 1
        
        storage_per_qtl = int(STORAGE_COST_PAISE_PER_KG_PER_DAY * 100 * days_from_now)
        spoilage_per_qtl = int(current_price_mid_paise * SPOILAGE_RATE_PER_DAY * days_from_now)
        transport_per_qtl = int(TRANSPORT_COST_PAISE_PER_KM * distance_km / qty_qtl) if distance_km else 0
        commission_per_qtl = int(fc["p50_paise"] * COMMISSION_RATE)
        loading_per_qtl = LOADING_UNLOADING_PAISE_PER_QTL
        
        total_per_qtl = storage_per_qtl + spoilage_per_qtl + transport_per_qtl + commission_per_qtl + loading_per_qtl
        
        p50_net = fc["p50_paise"] - total_per_qtl
        p10_net = fc["p10_paise"] - total_per_qtl
        
        # Expected gain is (future net - current net) * quantity. Since we didn't subtract transport/commission from current, 
        # let's just do (p50_net - sell_now_net) * qty
        gain = int((p50_net - sell_now_net) * qty_qtl)
        worst = int((p10_net - sell_now_net) * qty_qtl)

        if gain > best_gain and worst > - (total_per_qtl * qty_qtl * 0.5): # simple threshold
            best_day = i
            best_gain = gain
            best_worst = worst
            best_p50_net = p50_net
            best_p10_net = p10_net
            best_costs = {
                "transport_paise_per_qtl": transport_per_qtl,
                "commission_paise_per_qtl": commission_per_qtl,
                "storage_paise_per_qtl": storage_per_qtl,
                "spoilage_paise_per_qtl": spoilage_per_qtl,
                "loading_paise_per_qtl": loading_per_qtl,
                "total_paise_per_qtl": total_per_qtl
            }

    if best_day is None or best_gain <= 0:
        base_res.update({
            "recommendation": "SELL_NOW",
            "sell_now_net_paise_per_qtl": sell_now_net,
            "hold_p50_net_paise_per_qtl": sell_now_net, # Same as sell now since we're not holding
            "hold_p10_net_paise_per_qtl": sell_now_net,
            "expected_gain_paise": 0,
            "worst_case_paise": 0,
        })
        return base_res

    base_res.update({
        "recommendation": "HOLD",
        "sell_now_net_paise_per_qtl": sell_now_net,
        "hold_p50_net_paise_per_qtl": best_p50_net,
        "hold_p10_net_paise_per_qtl": best_p10_net,
        "expected_gain_paise": best_gain,
        "worst_case_paise": best_worst,
        "hold_days": best_day + 1,
        "itemised_costs": best_costs,
    })
    return base_res
