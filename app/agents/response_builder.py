"""Response builder: constructs cards, citations, ui_action, and fallbacks in code.

The LLM NEVER writes cards or citations directly. Every card and citation comes
from deterministic tool outputs; `ui_action` is restricted to whitelisted screens.
"""
from __future__ import annotations

from typing import Any, Optional

from app.agents.tool_bridge import ExecutedToolCall, resolve_allowed_screen
from app.nlp.messages import get_message
from app.schemas.agent import AgentCard, Citation, UiAction


def build_cards(executed: list[ExecutedToolCall]) -> list[AgentCard]:
    """Extract verified `AgentCard` objects from executed tool results."""
    cards: list[AgentCard] = []
    seen_types: set[str] = set()
    # Keep latest card of each type, preserving order of first appearance.
    by_type: dict[str, AgentCard] = {}
    order: list[str] = []
    for item in executed:
        if not item.envelope.ok or not item.envelope.card:
            continue
        raw_card = item.envelope.card
        ctype = raw_card.get("type")
        cdata = raw_card.get("data") or {}
        if not ctype:
            continue
        try:
            card = AgentCard(type=ctype, data=dict(cdata))
        except Exception:
            continue
        if ctype not in seen_types:
            seen_types.add(ctype)
            order.append(ctype)
        by_type[ctype] = card
    for ctype in order:
        cards.append(by_type[ctype])
    return cards


def build_citations(executed: list[ExecutedToolCall]) -> list[Citation]:
    """Deduplicate and return source citations from tools and RAG chunks."""
    citations: list[Citation] = []
    seen: set[tuple[str, Optional[str], Optional[str]]] = set()
    for item in executed:
        if not item.envelope.ok:
            continue
        for c in item.citations:
            src = str(c.get("source") or "").strip()
            if not src:
                continue
            key = (src, c.get("chunk_id"), c.get("title"))
            if key in seen:
                continue
            seen.add(key)
            citations.append(
                Citation(
                    source=src,
                    title=c.get("title"),
                    as_of=c.get("as_of"),
                    chunk_id=c.get("chunk_id"),
                    section_title=c.get("section_title"),
                )
            )
    return citations


def build_ui_action(
    executed: list[ExecutedToolCall],
    model_ui_action: Optional[dict[str, Any]] = None,
) -> Optional[UiAction]:
    """Select and validate `ui_action` against the `FarmerScreen` whitelist."""
    # Tool-emitted actions take precedence over model suggestions because they
    # carry verified canonical params (commodity_id, market_id, qty_kg).
    for item in reversed(executed):
        if not item.envelope.ok or not item.ui_action:
            continue
        raw = item.ui_action
        screen = resolve_allowed_screen(str(raw.get("target_screen") or ""))
        if screen is None:
            continue
        action_type = raw.get("type") if raw.get("type") in ("OFFER_NAVIGATION", "PREFILL") else "OFFER_NAVIGATION"
        return UiAction(
            type=action_type,
            target_screen=screen,
            cta_label=str(raw.get("cta_label") or "Open"),
            params=dict(raw.get("params") or {}),
        )

    if isinstance(model_ui_action, dict):
        screen = resolve_allowed_screen(str(model_ui_action.get("target_screen") or ""))
        if screen is not None:
            params = model_ui_action.get("params")
            return UiAction(
                type="OFFER_NAVIGATION",
                target_screen=screen,
                cta_label=str(model_ui_action.get("cta_label") or "Open"),
                params=dict(params) if isinstance(params, dict) else {},
            )
    return None


def normalize_quick_replies(raw: Any) -> list[str]:
    if not isinstance(raw, list):
        return []
    cleaned = [str(item).strip() for item in raw if str(item or "").strip()]
    return cleaned[:3]


def build_card_fallback_reply(cards: list[AgentCard], target_lang: str) -> str:
    """Pre-translated fallback reply optionally enriched with exact card numbers."""
    base = get_message("FALLBACK", target_lang)
    if not cards:
        return base
    card = cards[0]
    d = card.data
    if card.type == "PRICE_SNAPSHOT" and d.get("modal_paise_per_qtl"):
        rupees = int(round(int(d["modal_paise_per_qtl"]) / 100))
        crop = d.get("commodity_mr") if target_lang == "mr" and d.get("commodity_mr") else d.get("commodity", "")
        mandi = d.get("mandi_mr") if target_lang == "mr" and d.get("mandi_mr") else d.get("mandi", "")
        if target_lang == "mr":
            return f"{base} ({crop} @ {mandi}: ₹{rupees}/क्विंटल)"
        if target_lang == "hi":
            return f"{base} ({crop} @ {mandi}: ₹{rupees}/क्विंटल)"
        return f"{base} ({crop} @ {mandi}: Rs {rupees}/quintal)"
    if card.type == "WINDOW_VERDICT" and d.get("action"):
        action = d["action"]
        if action == "NO_ADVICE":
            return get_message("NO_ADVICE", target_lang)
        crop = d.get("commodity_mr") if target_lang == "mr" and d.get("commodity_mr") else d.get("commodity", "")
        mandi = d.get("mandi_mr") if target_lang == "mr" and d.get("mandi_mr") else d.get("mandi", "")
        return f"{base} ({crop} @ {mandi}: {action})"
    return base


__all__ = [
    "build_card_fallback_reply",
    "build_cards",
    "build_citations",
    "build_ui_action",
    "normalize_quick_replies",
]
