"""A1 resolve_place_or_crop · B1 get_mandi_price · B3 get_price_forecast."""

from __future__ import annotations

from typing import Literal, Optional

from pydantic import BaseModel, Field

from app.agents.tools import _common
from app.agents.tools.base import ToolContext, ToolFailure, ToolResult, navigate, tool
from app.services import price_service
from app.utils.id_resolver import resolve

_KIND = {"crop": "commodity", "mandi": "market", "district": "district"}


# ── A1 ──────────────────────────────────────────────────────────────────────

class ResolveArgs(BaseModel):
    text: str = Field(..., description="The name as the farmer said it, in any language or spelling, e.g. 'कांदा', 'kanda', 'Lasalgaon', 'निफाड'.")
    kind: Literal["crop", "mandi", "district"] = Field(..., description="What the name refers to.")


@tool("resolve_place_or_crop",
      "Turn a crop, mandi or district name the farmer said (Marathi, Hindi, English or "
      "colloquial) into the platform's canonical entry. Returns candidates when the name "
      "is ambiguous so you can ask which one they meant.",
      ResolveArgs)
async def resolve_place_or_crop(ctx: ToolContext, args: ResolveArgs) -> ToolResult:
    entity = await resolve(ctx.db, _KIND[args.kind], args.text)
    return ToolResult(data={"match": entity.as_dict()})


# ── B1 ──────────────────────────────────────────────────────────────────────

class PriceArgs(BaseModel):
    crop: Optional[str] = Field(None, description="Crop name or id. Omit to use the crop on the farmer's current screen.")
    mandi: Optional[str] = Field(None, description="Mandi name or id. Omit to use the mandi on the farmer's current screen.")
    compare_days: int = Field(7, ge=1, le=30, description="Compare today's rate with the rate this many days earlier.")


@tool("get_mandi_price",
      "Latest observed mandi rate for a crop (modal, min, max in paise per quintal), "
      "arrivals, change versus a week earlier, the data source and its date. "
      "Use for 'what is today's rate?' questions. Never estimate a rate yourself.",
      PriceArgs)
async def get_mandi_price(ctx: ToolContext, args: PriceArgs) -> ToolResult:
    commodity = await _common.crop(ctx, args.crop)
    market = await _common.mandi(ctx, args.mandi)
    snap = await price_service.mandi_snapshot(ctx.db, commodity.id, market.id, args.compare_days)
    if snap is None:
        raise ToolFailure("NO_DATA", f"No price for {commodity.name} at {market.name} in the last 30 days.")

    data = {"commodity": commodity.as_dict(), "market": market.as_dict(), **snap}
    card = {"type": "PRICE_SNAPSHOT", "data": {
        "commodity": commodity.name, "commodity_mr": commodity.name_mr,
        "mandi": market.name, "mandi_mr": market.name_mr,
        "modal_paise_per_qtl": snap["modal_paise_per_qtl"],
        "min_paise_per_qtl": snap["min_paise_per_qtl"],
        "max_paise_per_qtl": snap["max_paise_per_qtl"],
        "change_bps": snap["change_bps"],
        "obs_date": snap["obs_date"],
        "source": snap["source"],
    }}
    return ToolResult(
        data=data, card=card,
        ui_action=navigate(ctx, "PricesIndex", {"commodity_id": commodity.slug, "market_id": market.slug}),
        citation={"source": snap["source"], "as_of": snap["obs_date"]},
    )


# ── B3 ──────────────────────────────────────────────────────────────────────

class ForecastArgs(BaseModel):
    crop: Optional[str] = Field(None, description="Crop name or id. Omit to use the crop on screen.")
    mandi: Optional[str] = Field(None, description="Mandi name or id. Omit to use the mandi on screen.")
    horizon_days: int = Field(14, ge=1, le=14, description="How many days ahead (max 14).")


@tool("get_price_forecast",
      "The price model's forecast for the next days: expected price (p50) with a low (p10, "
      "the worst 1-in-10 case) to high (p90) band, in paise per quintal. Returns NO_DATA "
      "when the model is unavailable — then say you don't have a forecast; never invent one.",
      ForecastArgs)
async def get_price_forecast(ctx: ToolContext, args: ForecastArgs) -> ToolResult:
    commodity = await _common.crop(ctx, args.crop)
    market = await _common.mandi(ctx, args.mandi)
    latest = await price_service.latest_price(ctx.db, commodity.id, market.id)
    fc = price_service.forecast(commodity.name, market.name, args.horizon_days,
                                current_price_paise=latest["modal_paise_per_qtl"] if latest else None)
    if not fc["is_model"]:
        raise ToolFailure("NO_DATA", f"The forecast model has no forecast for {commodity.name} at {market.name} right now.")

    pts = fc["points"]
    first, last = pts[0], pts[-1]
    peak = max(pts, key=lambda p: p["p50_paise_per_qtl"])
    band_bps = ((last["p90_paise_per_qtl"] - last["p10_paise_per_qtl"]) * 10_000
                // last["p50_paise_per_qtl"]) if last["p50_paise_per_qtl"] else None
    data = {
        "commodity": commodity.as_dict(), "market": market.as_dict(),
        "source": fc["source"],
        "summary": {
            "first_date": first["target_date"], "first_p50_paise_per_qtl": first["p50_paise_per_qtl"],
            "last_date": last["target_date"], "last_p50_paise_per_qtl": last["p50_paise_per_qtl"],
            "peak_date": peak["target_date"], "peak_p50_paise_per_qtl": peak["p50_paise_per_qtl"],
            "lowest_p10_paise_per_qtl": min(p["p10_paise_per_qtl"] for p in pts),
            "highest_p90_paise_per_qtl": max(p["p90_paise_per_qtl"] for p in pts),
            "last_day_band_width_bps": band_bps,
        },
        "points": pts,
    }
    return ToolResult(
        data=data,
        ui_action=navigate(ctx, "PricesIndex", {"commodity_id": commodity.slug, "market_id": market.slug}),
        citation={"source": fc["source"], "title": "14-day LightGBM quantile forecast"},
    )
