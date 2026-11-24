"""Context builder: read-only farmer profile block + prompt-cache-ordered messages."""
from __future__ import annotations

import logging
from datetime import date
from typing import Any, Optional

from sqlalchemy import func, select
from sqlalchemy.ext.asyncio import AsyncSession

from app.agents.memory import MemoryTurn, SessionMemoryStore
from app.agents.prompts import system_prompt
from app.models.lot import Lot
from app.models.offer import Offer
from app.models.user import User
from app.schemas.agent import ScreenContext
from app.utils.id_resolver import load_catalog

logger = logging.getLogger("krishi.context")


async def build_farmer_profile_block(
    db: Optional[AsyncSession],
    user: Optional[User],
) -> str:
    """Build a compact read-only profile block from Postgres for the LLM prompt.

    Never writes to the database. Degrades cleanly for guest users or offline tests.
    """
    if user is None:
        return "Farmer profile: guest user (not logged in)."

    district_name = "unknown"
    crops_list: list[str] = []
    active_lots = 0
    open_offers = 0

    if db is not None:
        try:
            catalog = await load_catalog(db)
            if getattr(user, "district_id", None):
                dist = catalog.get("district", user.district_id)
                if dist is not None:
                    district_name = dist.name

            lot_rows = (
                await db.execute(
                    select(Lot.commodity_id)
                    .where(Lot.farmer_id == user.id)
                    .where(Lot.status == "active")
                )
            ).scalars().all()
            active_lots = len(lot_rows)
            seen: set[str] = set()
            for cid in lot_rows:
                comm = catalog.get("commodity", cid)
                if comm is not None and comm.name not in seen:
                    seen.add(comm.name)
                    crops_list.append(comm.name)

            open_offers = int(
                (
                    await db.execute(
                        select(func.count(Offer.id))
                        .where(Offer.farmer_id == user.id)
                        .where(Offer.status == "OPEN")
                    )
                ).scalar_one()
                or 0
            )
        except Exception as exc:
            logger.warning("Failed to build full profile block for user %s: %s", getattr(user, "id", "?"), exc)

    crops_str = ", ".join(crops_list) if crops_list else "none listed"
    village_str = f", village {user.village}" if getattr(user, "village", None) else ""
    role_str = (getattr(user, "role", None) or "FARMER").upper()
    return (
        f"Farmer profile: name {user.name}, role {role_str}, district {district_name}"
        f"{village_str}, crops [{crops_str}], active_lots {active_lots}, open_offers {open_offers}."
    )


def format_hints_line(hints: dict[str, Any]) -> str:
    """Render hints extracted from the farmer's original text."""
    if not hints:
        return "Hints from the farmer's original words: none"
    ordered = []
    for k in ("commodity", "mandi", "quantity_kg", "unit_unknown", "commodity_candidates", "mandi_candidates"):
        if k in hints:
            ordered.append(f"{k}={hints[k]}")
    if not ordered:
        for k, v in hints.items():
            ordered.append(f"{k}={v}")
    return "Hints from the farmer's original words: " + ", ".join(ordered)


def format_screen_context_line(
    screen_context: ScreenContext,
    today: Optional[date] = None,
) -> str:
    d = (today or date.today()).isoformat()
    parts = [f"Screen: {screen_context.current_screen or 'unknown'}"]
    if screen_context.active_commodity_id:
        parts.append(f"active_commodity={screen_context.active_commodity_id}")
    if screen_context.active_market_id:
        parts.append(f"active_market={screen_context.active_market_id}")
    if screen_context.active_lot_id:
        parts.append(f"active_lot={screen_context.active_lot_id}")
    parts.append(f"Today: {d}")
    return " | ".join(parts)


def build_context_messages(
    *,
    profile_block: str,
    history_turns: list[MemoryTurn],
    screen_context: ScreenContext,
    model_input_text: str,
    hints: dict[str, Any],
    pivot_on: bool = True,
    target_lang: str = "en",
    today: Optional[date] = None,
) -> list[dict[str, Any]]:
    """Assemble messages with stable prefix first to maximize provider prompt cache hits."""
    messages: list[dict[str, Any]] = [
        {"role": "system", "content": system_prompt(pivot_on=pivot_on, target_lang=target_lang)},
        {"role": "system", "content": profile_block},
    ]
    messages.extend(SessionMemoryStore.to_messages(history_turns))
    ctx_line = format_screen_context_line(screen_context, today=today)
    hint_line = format_hints_line(hints)
    messages.append(
        {
            "role": "user",
            "content": f"[{ctx_line}]\n{model_input_text}\n{hint_line}",
        }
    )
    return messages


__all__ = [
    "build_context_messages",
    "build_farmer_profile_block",
    "format_hints_line",
    "format_screen_context_line",
]
