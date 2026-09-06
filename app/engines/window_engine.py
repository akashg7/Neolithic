"""Window + Refusal Engine — computes SELL/HOLD/SPLIT/NO_ADVICE + pledge quote.

Delegates to the pure decision logic in app.domain.window.decide() and
app.domain.pledge.quote(), then adapts the result to the frontend contract
(per-quintal costs, recommendation enum, pledge_quote object).
"""

from __future__ import annotations

from datetime import datetime, date

from app.domain.window import decide
from app.domain.window import GAIN_BELOW_COST as _GAIN_BELOW_COST
from app.domain.window import MODEL_UNAVAILABLE as _MODEL_UNAVAILABLE
from app.domain.costs import compute_costs
from app.domain.assessed_value import assessed_value
from app.domain.pledge import quote as pledge_quote
from app.domain.constants import FORECAST_HORIZON_DAYS
from app.engines.price_engine import price_engine

# Configurable thresholds
BAND_WIDTH_THRESHOLD = 0.35  # 35%
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
    horizon_days: int = 14,
    grade: str = "A",
    history_rows: int = 400,
) -> dict:
    """Compute the full WindowRes dict.

<<<<<<< HEAD
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
        "costs": {
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
            "action": "NO_ADVICE",
            "refusal_reason": "BAND_TOO_WIDE",
            "explain_en": "Price forecast is too uncertain due to recent high volatility.",
            "explain_mr": "नुकत्याच झालेल्या चढउतारांमुळे किमतीचा अंदाज खूप अनिश्चित आहे."
        })
=======
    Uses the real LightGBM forecast (via domain.window.decide) when models
    are loaded; otherwise domain.decide refuses with NO_ADVICE rather than
    fabricating a number.

    Returns every key the frontend WindowRes schema expects, always present.
    """
    as_of = datetime.now()

    # Call the pure decision engine — never raises.
    result = decide(
        commodity=crop,
        market=mandi,
        spot_price_paise_per_qtl=current_price_mid_paise,
        quantity_kg=quantity_kg,
        distance_km=distance_km,
        history_rows=history_rows,
        as_of=as_of,
    )

    # Confidence enum: low|medium|high -> LOW|MEDIUM|HIGH
    conf_map = {"low": "LOW", "medium": "MEDIUM", "high": "HIGH"}
    confidence = conf_map.get(result.confidence, "LOW")

    # Per-quintal cost breakdown from the decision's chosen hold day.
    costs = result.costs
    qty_qtl = _qty_qtl(quantity_kg)
    itemised_costs = {
        "transport_paise_per_qtl": costs.transport_paise // qty_qtl,
        "commission_paise_per_qtl": costs.commission_paise // qty_qtl,
        "loading_paise_per_qtl": costs.loading_paise // qty_qtl,
        "storage_paise_per_qtl": costs.storage_paise // qty_qtl,
        "spoilage_paise_per_qtl": costs.spoilage_paise // qty_qtl,
        "total_paise_per_qtl": costs.total_paise // qty_qtl,
    }

    # Sell-now net (per qtl) — used by the frontend identities.
    sell_now_net_per_qtl = current_price_mid_paise - (
        compute_costs(current_price_mid_paise, quantity_kg, distance_km, days=0).total_paise // qty_qtl
    )

    base_res: dict = {
        "recommendation": result.action,          # SELL_NOW | HOLD | SPLIT | NO_ADVICE
        "confidence": confidence,
        "band_width_bps": result.band_width_bps,
        "sell_now_net_paise_per_qtl": sell_now_net_per_qtl,
        "hold_p50_net_paise_per_qtl": 0,
        "hold_p10_net_paise_per_qtl": 0,
        "expected_gain_paise": result.expected_gain_paise,
        "worst_case_paise": result.worst_case_paise,
        "itemised_costs": itemised_costs,
        "hold_days": result.hold_days if result.action in ("HOLD", "SPLIT") else None,
        "model_card": {"mase": 1.2, "coverage_80_bps": 8500},  # filled from model_meta in Phase 5
        "data_source": "AGMARKNET_ML" if price_engine._loaded else "SYNTHETIC",
        "pledge_quote": None,
        "alt_market": None,
        "refusal_reason": result.refusal_reason,
        "explain_mr": result.explain_mr,
        "explain_en": result.explain_en,
    }

    # NO_ADVICE: hold_p50/p10 nets are null-equivalent (0) per frontend contract.
    if result.action == "NO_ADVICE":
>>>>>>> 1f3d4c01e186ef4bc3b68b6daee889a5d50fce10
        return base_res

    # ── For HOLD/SPLIT: compute hold-day nets (per qtl) ────────────────
    if result.action in ("HOLD", "SPLIT") and result.hold_days > 0:
        # Rebuild the chosen hold-day's per-qtl costs so nets are consistent.
        hold_costs_qtl = {
            "storage_paise_per_qtl": 5 * 100 * result.hold_days,  # ₹5/kg/day
            "spoilage_paise_per_qtl": int(current_price_mid_paise * 0.002 * result.hold_days),
            "loading_paise_per_qtl": 2000,  # ₹20/qtl
        }
        # p50 net at chosen day = p50 forecast - holding costs.
        # We derive p50/p10 from the domain result's own cost total.
        hold_p50_net = (current_price_mid_paise
                        + result.expected_gain_paise // _qty_qtl(quantity_kg)
                        - result.costs.total_paise // qty_qtl)
        base_res["hold_p50_net_paise_per_qtl"] = hold_p50_net
        base_res["hold_p10_net_paise_per_qtl"] = max(0, hold_p50_net - result.band_width_bps * qty_qtl // 10000)
        base_res["itemised_costs"].update(hold_costs_qtl)
        base_res["itemised_costs"]["total_paise_per_qtl"] = (
            base_res["itemised_costs"]["storage_paise_per_qtl"]
            + base_res["itemised_costs"]["spoilage_paise_per_qtl"]
            + base_res["itemised_costs"]["loading_paise_per_qtl"]
            + 0  # transport/commission already in costs for the whole lot
        )

        # ── Pledge quote (only on HOLD/SPLIT with positive gain) ───────
        if result.expected_gain_paise > 0:
            p10_fc = current_price_mid_paise  # conservative basis
            try:
                forecast = price_engine.predict(mandi, crop, datetime.now().isoformat())
                p10_fc = forecast.get("p10_paise", current_price_mid_paise)
            except Exception:
                pass
            av = assessed_value(grade, quantity_kg, p10_fc)
            pq = pledge_quote(
                assessed_value_paise=av,
                expected_gain_paise=result.expected_gain_paise,
                days=result.hold_days,
            )
            if pq is not None:
                base_res["pledge_quote"] = {
                    "loan_paise": pq.loan_paise,
                    "interest_paise": pq.interest_paise,
                    "net_benefit_paise": pq.net_benefit_paise,
                    "assessed_value_paise": pq.assessed_value_paise,
                    "days": pq.days,
                    "ltv_bps": pq.ltv_bps,
                    "rate_bps_annual": pq.rate_bps_annual,
                    "warehouse_id": pq.warehouse_id,
                    "is_wdra_registered": pq.is_wdra_registered,
                    "disclaimer": pq.disclaimer,
                }

<<<<<<< HEAD
    # Baseline costs that apply even if selling today (transport, commission, loading)
    baseline_transport = int(TRANSPORT_COST_PAISE_PER_KM * distance_km / qty_qtl) if distance_km else 0
    baseline_commission = int(current_price_mid_paise * COMMISSION_RATE)
    baseline_loading = LOADING_UNLOADING_PAISE_PER_QTL
    baseline_total_costs = baseline_transport + baseline_commission + baseline_loading

    sell_now_net = current_price_mid_paise - baseline_total_costs

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
            "action": "SELL_NOW",
            "sell_now_net_paise_per_qtl": sell_now_net,
            "hold_p50_net_paise_per_qtl": sell_now_net,
            "hold_p10_net_paise_per_qtl": sell_now_net,
            "expected_gain_paise": 0,
            "worst_case_paise": 0,
            "costs": {
                "transport_paise_per_qtl": baseline_transport,
                "commission_paise_per_qtl": baseline_commission,
                "storage_paise_per_qtl": 0,
                "spoilage_paise_per_qtl": 0,
                "loading_paise_per_qtl": baseline_loading,
                "total_paise_per_qtl": baseline_total_costs
            },
            "explain_en": "Selling today is most profitable to avoid accruing storage and spoilage costs.",
            "explain_mr": "साठवणूक आणि खराब होण्याचा खर्च टाळण्यासाठी आजच विकणे सर्वाधिक फायदेशीर आहे."
        })
        return base_res

    base_res.update({
        "action": "HOLD",
        "sell_now_net_paise_per_qtl": sell_now_net,
        "hold_p50_net_paise_per_qtl": best_p50_net,
        "hold_p10_net_paise_per_qtl": best_p10_net,
        "expected_gain_paise": best_gain,
        "worst_case_paise": best_worst,
        "hold_days": best_day + 1,
        "costs": best_costs,
        "explain_en": f"Holding for {best_day + 1} days offers the best balance of potential price appreciation versus holding costs.",
        "explain_mr": f"{best_day + 1} दिवस थांबल्यास संभाव्य दरवाढ आणि साठवणूक खर्चाचा सर्वोत्तम समतोल मिळेल."
    })
=======
    # SELL_NOW: no hold-day nets; frontend shows 0/None.
>>>>>>> 1f3d4c01e186ef4bc3b68b6daee889a5d50fce10
    return base_res


def compute_pledge_quote(
    crop: str,
    mandi: str,
    grade: str,
    quantity_kg: int,
    expected_gain_paise: int,
    hold_days: int,
    forecast_p10_paise_per_qtl: int,
    warehouse_id: int | None = None,
    is_wdra_registered: bool = True,
) -> dict | None:
    """Compute a pledge quote or None (not worthwhile)."""
    from app.domain.pledge import quote as _quote
    from app.domain.assessed_value import assessed_value as _av
    av = _av(grade, quantity_kg, forecast_p10_paise_per_qtl)
    result = _quote(
        assessed_value_paise=av,
        expected_gain_paise=expected_gain_paise,
        days=hold_days,
        warehouse_id=warehouse_id,
        is_wdra_registered=is_wdra_registered,
    )
    if result is None:
        return None
    return {
        "loan_paise": result.loan_paise,
        "interest_paise": result.interest_paise,
        "net_benefit_paise": result.net_benefit_paise,
        "assessed_value_paise": result.assessed_value_paise,
        "days": result.days,
        "ltv_bps": result.ltv_bps,
        "rate_bps_annual": result.rate_bps_annual,
        "warehouse_id": result.warehouse_id,
        "is_wdra_registered": result.is_wdra_registered,
        "disclaimer": result.disclaimer,
    }
