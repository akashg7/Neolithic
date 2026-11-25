"""Pydantic schemas for Contract 1 (Agent Chat / Voice Chat) and Tool Envelopes.

Uses the Day-0 frozen Intent labels and ToolResult envelope from `app.contracts`.
Includes `turn_id` and `error_code` on `AgentChatResponse` per Backend Integration Plan §2.1,
and supports all farmer card types (`WINDOW_VERDICT`, `PRICE_SNAPSHOT`, `LOT_DRAFT`,
`CONFIRM_ACTION`, `RAG_CITATION`, `ONBOARD_PROFILE`).
"""
from __future__ import annotations

from typing import Any, Literal, Optional

from pydantic import BaseModel, Field, field_validator

from app.contracts import INTENT_LABELS, Intent, ToolResult

CardType = Literal[
    "WINDOW_VERDICT",
    "PRICE_SNAPSHOT",
    "LOT_DRAFT",
    "CONFIRM_ACTION",
    "RAG_CITATION",
    "ONBOARD_PROFILE",
]
UiActionType = Literal["OFFER_NAVIGATION", "PREFILL"]
LocaleCode = Literal["mr", "hi", "en"]


class ScreenContext(BaseModel):
    """Current UI state forwarded by the mobile/web app on every turn."""

    current_screen: Optional[str] = None
    active_commodity_id: Optional[str] = None
    active_market_id: Optional[str] = None
    active_lot_id: Optional[str] = None


class AgentChatRequest(BaseModel):
    """Request payload for `POST /api/v1/agent/chat`."""

    session_id: str = Field(..., min_length=1, max_length=128)
    message: str = Field(..., min_length=1, max_length=2000)
    locale: LocaleCode = "mr"
    screen_context: ScreenContext = Field(default_factory=ScreenContext)
    include_audio: bool = False

    @field_validator("session_id", "message")
    @classmethod
    def _strip_non_empty(cls, v: str) -> str:
        s = v.strip()
        if not s:
            raise ValueError("must not be blank")
        return s


class AgentCard(BaseModel):
    """Structured UI card built strictly in code from tool outputs."""

    type: CardType
    data: dict[str, Any] = Field(default_factory=dict)


class UiAction(BaseModel):
    """Deep-link or prefill action restricted to whitelisted app screens."""

    type: UiActionType = "OFFER_NAVIGATION"
    target_screen: str
    cta_label: str
    params: dict[str, Any] = Field(default_factory=dict)


class Citation(BaseModel):
    """Grounding source attribution from deterministic engines or RAG chunks."""

    source: str
    title: Optional[str] = None
    as_of: Optional[str] = None
    chunk_id: Optional[str] = None
    section_title: Optional[str] = None


class AgentChatResponse(BaseModel):
    """Contract 1 response returned by `/agent/chat` and `/agent/voice-chat`."""

    session_id: str
    turn_id: str
    transcript: str
    intent_detected: Intent
    reply_text: str
    audio_base64: Optional[str] = None
    cards: list[AgentCard] = Field(default_factory=list)
    ui_action: Optional[UiAction] = None
    citations: list[Citation] = Field(default_factory=list)
    quick_replies: list[str] = Field(default_factory=list, max_length=3)
    error_code: Optional[str] = None


class SessionDeleteResponse(BaseModel):
    """Response for `DELETE /api/v1/agent/session/{session_id}`."""

    ok: bool = True
    session_id: str
    cleared: bool = True


__all__ = [
    "INTENT_LABELS",
    "Intent",
    "ToolResult",
    "CardType",
    "UiActionType",
    "LocaleCode",
    "ScreenContext",
    "AgentChatRequest",
    "AgentCard",
    "UiAction",
    "Citation",
    "AgentChatResponse",
    "SessionDeleteResponse",
]
