"""Wave-1 tool behaviour: contract, confirm-only writes, no silent defaults."""

import json

import pytest

from app.agents.tools import TOOL_REGISTRY, ToolContext, run_tool, tool_schemas
from app.agents.tools import decision as decision_mod
from app.dependencies.auth import get_optional_user
from app.services import price_service, window_service

WAVE_1 = {"resolve_place_or_crop", "get_mandi_price", "get_price_forecast", "get_sale_window",
          "draft_lot", "create_lot", "run_quality_check", "get_lot_price_band", "open_screen"}

SNAP = {"obs_date": "2026-11-24", "min_paise_per_qtl": 180000, "max_paise_per_qtl": 240000,
        "modal_paise_per_qtl": 215000, "arrivals_qtl": 12000, "source": "AGMARKNET",
        "prev_obs_date": "2026-11-17", "prev_modal_paise_per_qtl": 200000,
        "change_paise_per_qtl": 15000, "change_bps": 750}


def ctx(user=None, locale="mr", **screen):
    return ToolContext(db=None, user=user, locale=locale, screen=screen)


# ── contract ────────────────────────────────────────────────────────────────

def test_wave1_registered_and_schemas_are_json():
    assert WAVE_1 <= set(TOOL_REGISTRY)
    schemas = tool_schemas()
    json.dumps(schemas, ensure_ascii=False)
    for s in schemas:
        props = s["parameters"].get("properties", {})
        # identity must come from the JWT, never from the LLM
        assert not {"user_id", "farmer_id", "buyer_id"} & set(props), s["name"]


def test_write_tools_are_marked_and_need_login():
    assert TOOL_REGISTRY["create_lot"].kind == "write"
    assert TOOL_REGISTRY["create_lot"].requires_login


@pytest.mark.asyncio
async def test_unknown_tool():
    r = await run_tool("sell_everything", ctx(), {})
    assert r["ok"] is False and r["error"]["code"] == "UNKNOWN_TOOL"


@pytest.mark.asyncio
async def test_optional_user_without_header_is_guest():
    assert await get_optional_user(None, users=None) is None


# ── A1 ──────────────────────────────────────────────────────────────────────

@pytest.mark.asyncio
async def test_resolve_tool():
    r = await run_tool("resolve_place_or_crop", ctx(), {"text": "kanda", "kind": "crop"})
    assert r["ok"] and r["data"]["match"]["slug"] == "cmd_onion"
    r = await run_tool("resolve_place_or_crop", ctx(), {"text": "pimpal", "kind": "mandi"})
    assert r["error"]["code"] == "AMBIGUOUS" and len(r["error"]["candidates"]) == 2
    r = await run_tool("resolve_place_or_crop", ctx(), {"text": "dragonfruit", "kind": "crop"})
    assert r["error"]["code"] == "NOT_FOUND"


# ── B1 ──────────────────────────────────────────────────────────────────────

@pytest.mark.asyncio
async def test_price_needs_a_crop_never_defaults():
    r = await run_tool("get_mandi_price", ctx(), {})
    assert r["error"]["code"] == "NEEDS_INPUT" and r["error"]["missing"] == ["crop"]


@pytest.mark.asyncio
async def test_price_uses_screen_context(monkeypatch):
    async def snap(db, c, m, d=7):
        assert (c, m) == (1, 1)
        return dict(SNAP)
    monkeypatch.setattr(price_service, "mandi_snapshot", snap)
    r = await run_tool("get_mandi_price", ctx(active_commodity_id="cmd_onion",
                                              active_market_id="mkt_lasalgaon"), {})
    assert r["ok"]
    assert r["card"]["type"] == "PRICE_SNAPSHOT"
    assert r["card"]["data"]["modal_paise_per_qtl"] == 215000
    assert r["citation"] == {"source": "AGMARKNET", "as_of": "2026-11-24"}


@pytest.mark.asyncio
async def test_price_no_data(monkeypatch):
    async def none(*a, **k):
        return None
    monkeypatch.setattr(price_service, "mandi_snapshot", none)
    r = await run_tool("get_mandi_price", ctx(), {"crop": "कांदा", "mandi": "लासलगाव"})
    assert r["error"]["code"] == "NO_DATA"


# ── B3 ──────────────────────────────────────────────────────────────────────

async def _latest(*a, **k):
    return dict(SNAP)


@pytest.mark.asyncio
async def test_forecast_refuses_synthetic(monkeypatch):
    monkeypatch.setattr(price_service, "latest_price", _latest)
    monkeypatch.setattr(price_service, "forecast",
                        lambda c, m, h=14, current_price_paise=None: {"points": [{"p50_paise_per_qtl": 1}], "source": "SYNTHETIC", "is_model": False})
    r = await run_tool("get_price_forecast", ctx(), {"crop": "onion", "mandi": "lasalgaon"})
    assert r["error"]["code"] == "NO_DATA"


@pytest.mark.asyncio
async def test_forecast_summary(monkeypatch):
    monkeypatch.setattr(price_service, "latest_price", _latest)
    pts = [{"target_date": f"2026-11-{25 + i}", "p10_paise_per_qtl": 180000 + i * 1000,
            "p50_paise_per_qtl": 210000 + i * 2000, "p90_paise_per_qtl": 240000 + i * 3000}
           for i in range(3)]
    monkeypatch.setattr(price_service, "forecast",
                        lambda c, m, h=14, current_price_paise=None: {"points": pts, "source": "AGMARKNET_SOTA", "is_model": True})
    r = await run_tool("get_price_forecast", ctx(), {"crop": "onion", "mandi": "lasalgaon", "horizon_days": 3})
    s = r["data"]["summary"]
    assert s["peak_p50_paise_per_qtl"] == 214000 and s["lowest_p10_paise_per_qtl"] == 180000


# ── C1 ──────────────────────────────────────────────────────────────────────

WINDOW_RESULT = {
    "action": "HOLD", "recommendation": "HOLD", "confidence": "MEDIUM", "hold_days": 5,
    "band_width_bps": 2100, "expected_gain_paise": 185000, "worst_case_paise": 40000,
    "sell_now_net_paise_per_qtl": 205000, "itemised_costs": {"total_paise_per_qtl": 9000},
    "pledge_quote": None, "refusal_reason": None, "explain_mr": "थांबा", "explain_en": "Hold",
    "data_source": "AGMARKNET_ML",
}


@pytest.mark.asyncio
async def test_sale_window_converts_bori_and_builds_card(monkeypatch, farmer):
    seen = {}

    async def fake(db, **kw):
        seen.update(kw)
        return {**WINDOW_RESULT, "inputs": {
            "commodity": {"slug": "cmd_onion", "name": "Onion", "name_mr": "कांदा", "id": 1},
            "market": {"slug": "mkt_lasalgaon", "name": "Lasalgaon APMC", "name_mr": "लासलगाव", "id": 1},
            "quantity_kg": kw["quantity_kg"], "transport_included": True,
            "spot_price_source": "AGMARKNET", "spot_price_date": "2026-11-24"}}
    monkeypatch.setattr(decision_mod, "sale_window", fake)
    r = await run_tool("get_sale_window", ctx(farmer),
                       {"crop": "कांदा", "mandi": "लासलगाव", "quantity": 20, "unit": "bori"})
    assert r["ok"], r
    assert seen["quantity_kg"] == 1000          # 20 bori, not 20
    assert seen["commodity_ref"] == 1 and seen["market_ref"] == 1
    assert r["card"]["type"] == "WINDOW_VERDICT" and r["card"]["data"]["hold_days"] == 5
    assert r["ui_action"]["target_screen"] == "S9_Verdict"
    assert r["ui_action"]["params"]["commodity_id"] == "cmd_onion"


@pytest.mark.asyncio
async def test_sale_window_without_quantity_asks():
    r = await run_tool("get_sale_window", ctx(), {"crop": "onion", "mandi": "lasalgaon"})
    assert r["error"]["code"] == "NEEDS_INPUT" and "quantity" in r["error"]["missing"]


# window_service itself: no invented inputs

@pytest.mark.asyncio
async def test_window_service_missing_mandi():
    with pytest.raises(window_service.WindowInputError) as exc:
        await window_service.sale_window(None, commodity_ref="onion", market_ref=None, quantity_kg=1000)
    assert exc.value.missing == ["mandi"]


@pytest.mark.asyncio
async def test_window_service_no_price_means_no_data(monkeypatch):
    async def no_obs(*a, **k):
        return None
    monkeypatch.setattr(price_service, "latest_price", no_obs)
    monkeypatch.setattr(window_service.price_engine, "predict",
                        lambda *a, **k: {"p50_paise": 220000, "source": "SYNTHETIC"})
    with pytest.raises(window_service.NoPriceDataError):
        await window_service.sale_window(None, commodity_ref="onion", market_ref="lasalgaon", quantity_kg=1000)


@pytest.mark.asyncio
async def test_window_service_real_distance_and_observed_price(monkeypatch, farmer):
    async def obs(*a, **k):
        return dict(SNAP)
    captured = {}

    def compute(**kw):
        captured.update(kw)
        return dict(WINDOW_RESULT)
    monkeypatch.setattr(price_service, "latest_price", obs)
    monkeypatch.setattr(window_service, "compute_sale_window", compute)

    r = await window_service.sale_window(None, commodity_ref="cmd_onion", market_ref="mkt_lasalgaon",
                                         quantity_kg=1000, user=farmer)
    assert captured["current_price_mid_paise"] == 215000      # observed, not 220000
    assert 10 < captured["distance_km"] < 30 and captured["distance_km"] != 50.0
    assert r["inputs"]["distance_source"] == "profile"

    r = await window_service.sale_window(None, commodity_ref="cmd_onion", market_ref="mkt_lasalgaon",
                                         quantity_kg=1000, user=None)
    assert captured["distance_km"] == 0.0 and r["inputs"]["transport_included"] is False


# ── D1 / D2 ─────────────────────────────────────────────────────────────────

@pytest.mark.asyncio
async def test_draft_lot_from_speech(monkeypatch):
    async def obs(*a, **k):
        return dict(SNAP)
    monkeypatch.setattr(price_service, "latest_price", obs)
    r = await run_tool("draft_lot", ctx(), {"crop": "कांदा", "quantity": 20, "unit": "bori", "mandi": "लासलगाव"})
    d = r["data"]
    assert d["quantity_kg"] == 1000 and d["commodity"]["slug"] == "cmd_onion"
    assert d["missing"] == ["expected_price_rupees_per_qtl"] and not d["ready"]
    assert d["suggested_price"]["paise_per_qtl"] == 215000
    assert r["card"]["type"] == "LOT_DRAFT" and r["ui_action"]["type"] == "PREFILL"


@pytest.mark.asyncio
async def test_draft_lot_unknown_crop_is_missing_not_error():
    r = await run_tool("draft_lot", ctx(), {"crop": "dragonfruit", "quantity": 5, "unit": "quintal"})
    assert r["ok"] and "crop" in r["data"]["missing"]


@pytest.mark.asyncio
async def test_create_lot_guest_and_buyer(buyer):
    args = {"crop": "onion", "quantity": 20, "unit": "bori", "expected_price_rupees_per_qtl": 2200}
    assert (await run_tool("create_lot", ctx(), args))["error"]["code"] == "NEEDS_LOGIN"
    assert (await run_tool("create_lot", ctx(buyer), args))["error"]["code"] == "NOT_ALLOWED"


@pytest.mark.asyncio
async def test_create_lot_returns_confirm_card_only(farmer):
    r = await run_tool("create_lot", ctx(farmer), {
        "crop": "कांदा", "quantity": 20, "unit": "bori",
        "expected_price_rupees_per_qtl": 2200, "mandi": "mkt_lasalgaon"})
    assert r["ok"] and r["kind"] == "write"
    card = r["card"]
    assert card["type"] == "CONFIRM_ACTION" and card["data"]["action"] == "CREATE_LOT"
    req = card["data"]["request"]
    assert req == {"method": "POST", "path": "/api/v1/lots", "body": {
        "commodity_id": "1", "qty_kg": 1000, "expected_price_paise": 220000, "market_id": "1"}}
    assert r["data"]["pending_confirmation"] is True


@pytest.mark.asyncio
async def test_create_lot_minimum_quantity(farmer):
    r = await run_tool("create_lot", ctx(farmer), {
        "crop": "onion", "quantity": 1, "unit": "bori", "expected_price_rupees_per_qtl": 2200})
    assert r["error"]["code"] == "NEEDS_INPUT"


# ── D3 ──────────────────────────────────────────────────────────────────────

@pytest.mark.asyncio
async def test_quality_check_asks_one_question_at_a_time():
    r = await run_tool("run_quality_check", ctx(locale="mr"), {"size_uniform": 3})
    d = r["data"]
    assert d["complete"] is False and d["next_question"]["field"] == "colour_uniform"
    assert d["next_question"]["text"] == "रंग किती सारखा आहे?"


@pytest.mark.asyncio
async def test_quality_check_grades_preview_without_lot():
    r = await run_tool("run_quality_check", ctx(locale="en"), {
        "size_uniform": 3, "colour_uniform": 3, "damage_pct": 2, "sprouting": 3,
        "moisture_feel": 3, "foreign_matter": 3})
    assert r["data"]["grade"] == "A" and r["card"] is None


@pytest.mark.asyncio
async def test_quality_check_rejects_out_of_scale():
    r = await run_tool("run_quality_check", ctx(), {"size_uniform": 5})
    assert r["error"]["code"] == "NEEDS_INPUT"


# ── D4 / G5 ─────────────────────────────────────────────────────────────────

@pytest.mark.asyncio
async def test_price_band_needs_login():
    r = await run_tool("get_lot_price_band", ctx(), {"lot_id": "3"})
    assert r["error"]["code"] == "NEEDS_LOGIN"


@pytest.mark.asyncio
async def test_open_screen_only_real_routes():
    ok = await run_tool("open_screen", ctx(locale="en"), {"target_screen": "S15_MyLots"})
    assert ok["ui_action"]["target_screen"] == "S15_MyLots" and ok["ui_action"]["cta_label"] == "Open"
    bad = await run_tool("open_screen", ctx(), {"target_screen": "S99_Hack"})
    assert bad["error"]["code"] == "NEEDS_INPUT"
    bad = await run_tool("open_screen", ctx(), {"target_screen": "S15_MyLots", "params": {"user_id": 7}})
    assert bad["error"]["code"] == "NEEDS_INPUT"
