"""G5 open_screen — one-tap deep link, restricted to real farmer routes."""

from __future__ import annotations

from typing import Literal

from pydantic import BaseModel, Field, field_validator

from app.agents.tools.base import ToolContext, ToolResult, navigate, tool

# Route names as registered in Krishi-Mitr/src/navigation/{FarmerTabs,RootNavigator,AuthStack}.tsx.
# The LLM can only pick from this list, so it can never invent a screen.
FarmerScreen = Literal[
    "S3_Profile", "S4_Home", "PricesIndex", "S8_ModelCard", "S9_Verdict", "S10_CostBreakdown",
    "S13_CropLoan", "S14_CounterOffer", "S15_MyLots", "S16_PoolSplit", "S17_CameraGuide",
    "S18_PhotoReview", "S19_Quantity", "S20_QualityDiagnostic", "S21_GradeReveal",
    "S22_PricePublish", "S23_PublishedRadar", "S24_LotDetail", "S25_BuyersForLot",
    "S27_Bargaining", "S28_CounterOffer", "S30_DealDone", "S31_DealsList", "S32_DealTracking",
    "S33_Settled", "S35_FarmerProfile", "S37_Talks", "S38_Notifications", "LanguageSwitcher",
    "Assistant",
]

_PARAM_KEYS = {"commodity_id", "market_id", "district_id", "lot_id", "offer_id",
               "transaction_id", "qty_kg"}


class OpenScreenArgs(BaseModel):
    target_screen: FarmerScreen = Field(..., description="The app screen to open.")
    params: dict[str, str | int] = Field(default_factory=dict, description="Ids to pre-select: commodity_id, market_id, district_id, lot_id, offer_id, transaction_id, qty_kg.")

    @field_validator("params")
    @classmethod
    def only_known_ids(cls, v: dict) -> dict:
        unknown = set(v) - _PARAM_KEYS
        if unknown:
            raise ValueError(f"unknown params: {sorted(unknown)}")
        return v


@tool("open_screen",
      "Offer a one-tap button that opens an app screen (e.g. My Lots, Deals, Crop Loan) with "
      "the right item pre-selected. Use when the farmer asks to go somewhere in the app.",
      OpenScreenArgs, kind="navigate")
async def open_screen(ctx: ToolContext, args: OpenScreenArgs) -> ToolResult:
    action = navigate(ctx, args.target_screen, dict(args.params),
                      label=("उघडा", "खोलें", "Open"))
    return ToolResult(data={"target_screen": args.target_screen, "params": dict(args.params)},
                      ui_action=action)
