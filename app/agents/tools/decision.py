"""C1 get_sale_window — SELL / HOLD / NO_ADVICE on real inputs."""

from __future__ import annotations

from typing import Literal, Optional

from pydantic import BaseModel, Field

from app.agents.tools import _common
from app.agents.tools.base import ToolContext, ToolResult, navigate, tool
from app.services.window_service import sale_window


class WindowArgs(BaseModel):
    lot_id: Optional[str] = Field(None, description="The farmer's lot id. When given, crop, mandi, quantity and grade come from the lot.")
    crop: Optional[str] = Field(None, description="Crop name or id (when there is no lot). Omit to use the crop on screen.")
    mandi: Optional[str] = Field(None, description="Mandi name or id (when there is no lot). Omit to use the mandi on screen.")
    quantity: Optional[float] = Field(None, gt=0, description="Quantity as the farmer said it, e.g. 20 for '20 bori'.")
    unit: Literal["kg", "quintal", "bori", "goni", "bag", "ton"] = Field("kg", description="Unit of `quantity`. 1 bori/goni/bag = 50 kg, 1 quintal = 100 kg.")
    grade: Optional[Literal["A", "B", "C"]] = Field(None, description="Quality grade if known.")


@tool("get_sale_window",
      "Should the farmer sell now or hold? Returns SELL_NOW / HOLD (for N days) / SPLIT / "
      "NO_ADVICE with expected gain, worst case (1-in-10) and itemised costs, all in paise. "
      "When the action is NO_ADVICE, explain the refusal reason and do not give advice.",
      WindowArgs)
async def get_sale_window(ctx: ToolContext, args: WindowArgs) -> ToolResult:
    # An explicit lot wins; with no crop/quantity named, fall back to the lot on screen.
    use_lot = bool(args.lot_id) or not (args.crop or args.quantity)
    lot_id = _common.lot_id_from(ctx, args.lot_id) if use_lot else None
    lat = lng = None
    if lot_id is not None:
        lot = await _common.owned_lot(ctx, lot_id)
        commodity_ref = lot.commodity_id
        market_ref = lot.market_id or args.mandi or ctx.screen_value("active_market_id")
        qty_kg = lot.quantity_qtl * 100
        grade = lot.grade if lot.grade in ("A", "B", "C") else args.grade
        lat, lng = lot.lat, lot.lng
    else:
        commodity_ref = (await _common.crop(ctx, args.crop)).id
        market_ref = (await _common.mandi(ctx, args.mandi)).id
        qty_kg = _common.quantity_kg(args.quantity, args.unit)
        grade = args.grade

    r = await sale_window(ctx.db, commodity_ref=commodity_ref, market_ref=market_ref,
                          quantity_kg=qty_kg, grade=grade, user=ctx.user, lat=lat, lng=lng)
    inp = r["inputs"]
    action = r.get("action") or r.get("recommendation")

    card = {"type": "WINDOW_VERDICT", "data": {
        "action": action,
        "hold_days": r.get("hold_days"),
        "expected_gain_paise": r.get("expected_gain_paise"),
        "worst_case_paise": r.get("worst_case_paise"),
        "sell_now_net_paise_per_qtl": r.get("sell_now_net_paise_per_qtl"),
        "refusal_reason": r.get("refusal_reason"),
        "commodity": inp["commodity"]["name"], "commodity_mr": inp["commodity"]["name_mr"],
        "mandi": inp["market"]["name"], "mandi_mr": inp["market"]["name_mr"],
        "quantity_kg": inp["quantity_kg"],
        "transport_included": inp["transport_included"],
        "pledge_available": r.get("pledge_quote") is not None,
    }}
    data = {k: r.get(k) for k in (
        "action", "confidence", "hold_days", "band_width_bps", "expected_gain_paise",
        "worst_case_paise", "sell_now_net_paise_per_qtl", "hold_p50_net_paise_per_qtl",
        "hold_p10_net_paise_per_qtl", "itemised_costs", "pledge_quote", "refusal_reason",
        "explain_mr", "explain_en", "data_source")}
    data["inputs"] = inp
    if lot_id is not None:
        data["lot_id"] = str(lot_id)

    return ToolResult(
        data=data, card=card,
        ui_action=navigate(ctx, "S9_Verdict", {
            "commodity_id": inp["commodity"]["slug"], "market_id": inp["market"]["slug"],
            "qty_kg": inp["quantity_kg"], **({"lot_id": str(lot_id)} if lot_id else {})}),
        citation={"source": "window_engine_v1", "data_source": r.get("data_source"),
                  "price_source": inp["spot_price_source"], "price_date": inp["spot_price_date"]},
    )
