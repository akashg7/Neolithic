"""D1 draft_lot · D2 create_lot · D3 run_quality_check · D4 get_lot_price_band.

D1 → D2 → D3 → D4 is the voice lot-creation flow: "माझ्याकडे २० बोरी कांदा आहे"
becomes a draft, then a Confirm card, then a graded lot with a fair price band.
D2 and the save step of D3 never write — they return CONFIRM_ACTION cards.
"""

from __future__ import annotations

from typing import Literal, Optional

from pydantic import BaseModel, Field

from app.agents.tools import _common
from app.agents.tools.base import (
    ToolContext, ToolFailure, ToolResult, confirm_card, navigate, tool,
)
from app.agents.tools.units import rupees_to_paise
from app.engines.grading_engine import grade as compute_grade
from app.services import lot_service, price_service
from app.utils.id_resolver import ResolveError, load_catalog

Unit = Literal["kg", "quintal", "bori", "goni", "bag", "ton"]
_MIN_LOT_KG = 100  # lots are stored in whole quintals


async def _try(coro):
    """Resolve what we can for a draft; a bad name becomes a 'missing' field, not a failure."""
    try:
        return await coro
    except (ToolFailure, ResolveError):
        return None


# ── D1 ──────────────────────────────────────────────────────────────────────

class DraftArgs(BaseModel):
    crop: Optional[str] = Field(None, description="Crop name or id. Omit to use the crop on screen.")
    quantity: Optional[float] = Field(None, gt=0, description="Quantity as said, e.g. 20 for '20 bori'.")
    unit: Unit = Field("kg", description="Unit of `quantity`. 1 bori/goni/bag = 50 kg, 1 quintal = 100 kg.")
    mandi: Optional[str] = Field(None, description="Mandi the farmer wants to sell at, if said.")
    expected_price_rupees_per_qtl: Optional[float] = Field(None, gt=0, description="Asking price in rupees per quintal, if the farmer said one.")


@tool("draft_lot",
      "Start a lot (a batch of produce to sell) from what the farmer said. Converts units, "
      "matches the crop and mandi, lists what is still missing, and suggests a price from "
      "today's observed mandi rate. Saves nothing — follow with create_lot.",
      DraftArgs)
async def draft_lot(ctx: ToolContext, args: DraftArgs) -> ToolResult:
    commodity = await _try(_common.crop(ctx, args.crop))
    market = await _try(_common.mandi(ctx, args.mandi))
    qty_kg = None
    if args.quantity is not None:
        qty_kg = _common.quantity_kg(args.quantity, args.unit)

    missing = []
    if commodity is None:
        missing.append("crop")
    if qty_kg is None:
        missing.append("quantity")
    elif qty_kg < _MIN_LOT_KG:
        missing.append("quantity")  # below one quintal can't be listed
    if args.expected_price_rupees_per_qtl is None:
        missing.append("expected_price_rupees_per_qtl")

    suggested = None
    if commodity is not None and market is not None:
        snap = await price_service.latest_price(ctx.db, commodity.id, market.id)
        if snap is not None:
            suggested = {"paise_per_qtl": snap["modal_paise_per_qtl"],
                         "source": snap["source"], "obs_date": snap["obs_date"]}

    expected_paise = rupees_to_paise(args.expected_price_rupees_per_qtl) if args.expected_price_rupees_per_qtl else None
    draft = {
        "commodity": commodity.as_dict() if commodity else None,
        "market": market.as_dict() if market else None,
        "quantity_kg": qty_kg,
        "stored_quantity_kg": (qty_kg // 100) * 100 if qty_kg else None,
        "expected_price_paise_per_qtl": expected_paise,
        "suggested_price": suggested,
        "missing": missing,
        "ready": not missing,
        "min_quantity_kg": _MIN_LOT_KG,
    }
    params = {k: v for k, v in {
        "commodity_id": commodity.slug if commodity else None,
        "market_id": market.slug if market else None,
        "qty_kg": qty_kg}.items() if v is not None}
    card = {"type": "LOT_DRAFT", "data": {
        "commodity": commodity.name if commodity else None,
        "commodity_mr": commodity.name_mr if commodity else None,
        "mandi": market.name if market else None,
        "quantity_kg": qty_kg,
        "expected_price_paise_per_qtl": expected_paise,
        "suggested_price_paise_per_qtl": suggested["paise_per_qtl"] if suggested else None,
        "missing": missing,
    }}
    return ToolResult(data=draft, card=card,
                      ui_action=navigate(ctx, "S19_Quantity", params, kind="PREFILL",
                                         label=("फॉर्ममध्ये भरा", "फ़ॉर्म में भरें", "Fill the form")))


# ── D2 ──────────────────────────────────────────────────────────────────────

class CreateLotArgs(BaseModel):
    crop: str = Field(..., description="Crop name or id.")
    quantity: float = Field(..., gt=0, description="Quantity as said, e.g. 20 for '20 bori'.")
    unit: Unit = Field("kg", description="Unit of `quantity`.")
    expected_price_rupees_per_qtl: float = Field(..., gt=0, description="Asking price in rupees per quintal, as the farmer confirmed it.")
    mandi: Optional[str] = Field(None, description="Mandi to sell at, if chosen.")


@tool("create_lot",
      "Prepare to save a new lot. Does NOT save: returns a Confirm card with the exact "
      "details; the lot is created only when the farmer taps Confirm. Only call after the "
      "farmer has agreed to the crop, quantity and price.",
      CreateLotArgs, kind="write", requires_login=True)
async def create_lot(ctx: ToolContext, args: CreateLotArgs) -> ToolResult:
    if (ctx.user.role or "").upper() not in ("FARMER", "FPO_ADMIN"):
        raise ToolFailure("NOT_ALLOWED", "Only farmers can create lots.")
    commodity = await _common.crop(ctx, args.crop)
    market = await _common.mandi(ctx, args.mandi) if args.mandi else None
    qty_kg = _common.quantity_kg(args.quantity, args.unit)
    if qty_kg < _MIN_LOT_KG:
        raise ToolFailure("NEEDS_INPUT", f"A lot needs at least {_MIN_LOT_KG} kg (1 quintal).", missing=["quantity"])
    price = rupees_to_paise(args.expected_price_rupees_per_qtl)

    body = {"commodity_id": str(commodity.id), "qty_kg": qty_kg,
            "expected_price_paise": price,
            "market_id": str(market.id) if market else None}
    stored = (qty_kg // 100) * 100
    summary = {
        "commodity": commodity.name, "commodity_mr": commodity.name_mr,
        "quantity_kg": qty_kg, "stored_quantity_kg": stored,
        "expected_price_paise_per_qtl": price,
        "mandi": market.name if market else None,
    }
    return ToolResult(
        data={"pending_confirmation": True, **summary,
              "note": None if stored == qty_kg else f"Lots are stored in whole quintals: {stored} kg."},
        card=confirm_card(ctx, action="CREATE_LOT", summary=summary,
                          method="POST", path="/api/v1/lots", body=body),
    )


# ── D3 ──────────────────────────────────────────────────────────────────────

# Same six questions as S20_QualityDiagnostic. Scales: 3 = best, 1 = worst
# (grading_engine convention); damage_pct is a 0-100 percentage.
_QUESTIONS: dict[str, dict] = {
    "size_uniform": {
        "mr": "दाण्यांचा / मालाचा आकार किती सारखा आहे?", "hi": "माल का आकार कितना एक जैसा है?",
        "en": "How uniform is the size?",
        "options": {3: "almost all the same", 2: "somewhat mixed", 1: "very mixed"}},
    "colour_uniform": {
        "mr": "रंग किती सारखा आहे?", "hi": "रंग कितना एक जैसा है?", "en": "How uniform is the colour?",
        "options": {3: "same colour", 2: "some variation", 1: "very uneven"}},
    "damage_pct": {
        "mr": "नुकसान किती % आहे?", "hi": "कितने % माल खराब है?", "en": "Roughly what % is damaged?",
        "options": "0-100"},
    "sprouting": {
        "mr": "कोंब फुटले आहेत का?", "hi": "क्या अंकुर निकले हैं?", "en": "Is there sprouting?",
        "options": {3: "none", 2: "a little", 1: "a lot"}},
    "moisture_feel": {
        "mr": "ओलावा कसा वाटतो?", "hi": "नमी कैसी लगती है?", "en": "How does the moisture feel?",
        "options": {3: "dry", 2: "slightly damp", 1: "wet"}},
    "foreign_matter": {
        "mr": "माती/काडीकचरा किती आहे?", "hi": "मिट्टी/कचरा कितना है?", "en": "How much soil or debris is mixed in?",
        "options": {3: "clean", 2: "some", 1: "a lot"}},
}


class QualityArgs(BaseModel):
    lot_id: Optional[str] = Field(None, description="Lot to save the grade on. Omit for a preview, or to use the lot on screen.")
    size_uniform: Optional[Literal[1, 2, 3]] = Field(None, description="3 = almost all same size, 2 = somewhat mixed, 1 = very mixed.")
    colour_uniform: Optional[Literal[1, 2, 3]] = Field(None, description="3 = same colour, 2 = some variation, 1 = very uneven.")
    damage_pct: Optional[int] = Field(None, ge=0, le=100, description="Percent of produce damaged, 0-100.")
    sprouting: Optional[Literal[1, 2, 3]] = Field(None, description="3 = none, 2 = a little, 1 = a lot.")
    moisture_feel: Optional[Literal[1, 2, 3]] = Field(None, description="3 = dry, 2 = slightly damp, 1 = wet.")
    foreign_matter: Optional[Literal[1, 2, 3]] = Field(None, description="3 = clean, 2 = some, 1 = a lot.")


@tool("run_quality_check",
      "Grade produce (A/B/C) from six self-check answers. Pass whatever answers you have; "
      "if any are missing it returns the next question to ask (one at a time). With all six "
      "it returns the grade and one improvement tip, plus a Confirm card to save it on the lot.",
      QualityArgs)
async def run_quality_check(ctx: ToolContext, args: QualityArgs) -> ToolResult:
    answers = {k: getattr(args, k) for k in _QUESTIONS}
    missing = [k for k, v in answers.items() if v is None]
    if missing:
        key = missing[0]
        q = _QUESTIONS[key]
        return ToolResult(data={
            "complete": False, "missing": missing,
            "next_question": {"field": key, "text": ctx.t(q["mr"], q["hi"], q["en"]),
                              "answer_scale": q["options"]},
            "answers_so_far": {k: v for k, v in answers.items() if v is not None},
        })

    g = compute_grade(answers)
    data = {"complete": True, "grade": g["grade"], "score": g["score"],
            "weakest_dimension": g["weakest_dimension"],
            "tip": ctx.t(g["tip_mr"], g["tip_en"], g["tip_en"]),
            "tip_mr": g["tip_mr"], "tip_en": g["tip_en"], "answers": answers}

    card = None
    lot_id = _common.lot_id_from(ctx, args.lot_id)
    if lot_id is not None and ctx.user is not None:
        await _common.owned_lot(ctx, lot_id)  # NOT_FOUND for someone else's lot
        data["lot_id"] = str(lot_id)
        card = confirm_card(ctx, action="SAVE_GRADE",
                            summary={"lot_id": str(lot_id), "grade": g["grade"], "score": g["score"]},
                            method="POST", path=f"/api/v1/lots/{lot_id}/assay", body=answers)
    return ToolResult(data=data, card=card)


# ── D4 ──────────────────────────────────────────────────────────────────────

class BandArgs(BaseModel):
    lot_id: Optional[str] = Field(None, description="The farmer's lot id. Omit to use the lot on screen.")


@tool("get_lot_price_band",
      "Fair asking-price band (low / mid / high, paise per quintal) for one of the farmer's "
      "lots, plus the sell-or-hold verdict for it.",
      BandArgs, requires_login=True)
async def get_lot_price_band(ctx: ToolContext, args: BandArgs) -> ToolResult:
    lot_id = _common.lot_id_from(ctx, args.lot_id)
    if lot_id is None:
        raise ToolFailure("NEEDS_INPUT", "Which lot?", missing=["lot_id"])
    res = await lot_service.get_price_suggestion(ctx.db, ctx.user, lot_id)  # 404 if not theirs
    out = res.model_dump()

    band = out["price_band"]
    if band.get("band_source") in ("SYNTHETIC", "NONE", None) or not band.get("mid_paise_per_qtl"):
        # Never quote an illustrative band as if it came from the model.
        out["price_band"] = None
        out["band_unavailable_reason"] = "The price model has no band for this crop and mandi right now."

    market = None
    if out.get("market_id"):
        from app.utils.id_resolver import resolve
        market = await resolve(ctx.db, "market", out["market_id"])
    return ToolResult(
        data=out,
        ui_action=navigate(ctx, "S22_PricePublish", {"lot_id": str(lot_id)},
                           label=("भाव ठरवा", "भाव तय करें", "Set your price")),
        citation={"source": band.get("band_source") or "NONE",
                  "mandi": market.name if market else None},
    )
