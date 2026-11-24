"""Small helpers shared by the tool modules."""

from __future__ import annotations

from sqlalchemy import select

from app.agents.tools.base import ToolContext, ToolFailure
from app.agents.tools.units import to_kg
from app.models.lot import Lot
from app.utils.id_resolver import RefEntity, resolve


async def crop(ctx: ToolContext, given: str | None) -> RefEntity:
    """The crop the farmer named, else the one on screen. Never a default crop."""
    ref = given or ctx.screen_value("active_commodity_id")
    if not ref:
        raise ToolFailure("NEEDS_INPUT", "Which crop?", missing=["crop"])
    return await resolve(ctx.db, "commodity", ref)


async def mandi(ctx: ToolContext, given: str | None) -> RefEntity:
    """The mandi the farmer named, else the one on screen. Never a default mandi."""
    ref = given or ctx.screen_value("active_market_id")
    if not ref:
        raise ToolFailure("NEEDS_INPUT", "Which mandi?", missing=["mandi"])
    return await resolve(ctx.db, "market", ref)


def quantity_kg(quantity: float | None, unit: str | None) -> int:
    if quantity is None:
        raise ToolFailure("NEEDS_INPUT", "How much quantity?", missing=["quantity"])
    try:
        return to_kg(quantity, unit or "kg")
    except ValueError as exc:
        raise ToolFailure("NEEDS_INPUT", str(exc), missing=["quantity", "unit"]) from exc


def lot_id_from(ctx: ToolContext, given: str | int | None) -> int | None:
    ref = given if given not in (None, "") else ctx.screen_value("active_lot_id")
    if ref in (None, ""):
        return None
    s = str(ref).strip()
    if not s.isdigit():
        raise ToolFailure("NOT_FOUND", f"Unknown lot {ref!r}")
    return int(s)


async def owned_lot(ctx: ToolContext, lot_id: int) -> Lot:
    """The farmer's own lot, or NOT_FOUND (also for someone else's lot)."""
    if ctx.user is None:
        raise ToolFailure("NEEDS_LOGIN", "Log in to see your lots.")
    lot = (await ctx.db.execute(select(Lot).where(Lot.id == lot_id))).scalar_one_or_none()
    if lot is None or lot.farmer_id != ctx.user.id:
        raise ToolFailure("NOT_FOUND", "Lot not found")
    return lot
