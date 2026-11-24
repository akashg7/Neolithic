"""Redis-backed session memory (DB 2) for the last 8 turns.

Key: `agent:mem:{session_id}`, TTL: 1800s (30 minutes).
Stores compact English turn summaries (never full raw tool payloads) so prompt
prefixes stay lean and translation runs only at the edges.
"""
from __future__ import annotations

import json
import logging
from dataclasses import dataclass, field
from typing import Any, Optional

from redis import asyncio as aioredis
from redis.exceptions import RedisError

from app.config import settings

logger = logging.getLogger("krishi.memory")

MEMORY_KEY_PREFIX = "agent:mem:"


@dataclass
class MemoryTurn:
    """One compact conversational turn stored in session memory."""

    user: str
    assistant: str
    intent: str = ""
    tool_summaries: list[str] = field(default_factory=list)

    def to_dict(self) -> dict[str, Any]:
        return {
            "user": self.user,
            "assistant": self.assistant,
            "intent": self.intent,
            "tool_summaries": self.tool_summaries,
        }

    @classmethod
    def from_dict(cls, data: dict[str, Any]) -> "MemoryTurn":
        return cls(
            user=str(data.get("user", "")),
            assistant=str(data.get("assistant", "")),
            intent=str(data.get("intent", "")),
            tool_summaries=[str(s) for s in (data.get("tool_summaries") or [])],
        )


def compact_tool_summary(tool_name: str, result: dict[str, Any]) -> str:
    """Distill a tool execution dict into a short single-line memory note."""
    if not result.get("ok"):
        err = result.get("error") or {}
        if isinstance(err, dict):
            return f"[{tool_name}: error={err.get('code', 'ERROR')} {err.get('message', '')}]"
        return f"[{tool_name}: error={err}]"

    data = result.get("data") or {}
    card = result.get("card") or {}
    ctype = card.get("type") if isinstance(card, dict) else None
    cdata = (card.get("data") if isinstance(card, dict) else None) or {}

    if tool_name in ("compute_sale_window", "get_sale_window"):
        return (
            f"[{tool_name}: action={data.get('action')}, hold_days={data.get('hold_days')}, "
            f"commodity={cdata.get('commodity')}, mandi={cdata.get('mandi')}, "
            f"qty_kg={cdata.get('quantity_kg')}, gain_paise={data.get('expected_gain_paise')}]"
        )
    if tool_name in ("get_price_forecast", "get_mandi_price"):
        comm = (data.get("commodity") or {}).get("name") or cdata.get("commodity")
        mkt = (data.get("market") or {}).get("name") or cdata.get("mandi")
        modal = data.get("modal_paise_per_qtl") or cdata.get("modal_paise_per_qtl")
        return f"[{tool_name}: commodity={comm}, mandi={mkt}, modal_paise={modal}]"
    if tool_name in ("create_lot_draft", "draft_lot", "create_lot"):
        return (
            f"[{tool_name}: card={ctype}, commodity={cdata.get('commodity')}, "
            f"qty_kg={cdata.get('quantity_kg')}, mandi={cdata.get('mandi')}]"
        )
    if tool_name in ("calculate_grade", "run_quality_check"):
        if data.get("complete"):
            return f"[{tool_name}: grade={data.get('grade')}, score={data.get('score')}]"
        nxt = (data.get("next_question") or {}).get("field")
        return f"[{tool_name}: incomplete, next={nxt}]"
    if tool_name == "get_farmer_portfolio":
        return (
            f"[{tool_name}: lots={len(data.get('active_lots') or [])}, "
            f"offers={len(data.get('open_offers') or [])}, "
            f"txns={len(data.get('transactions') or [])}]"
        )
    if tool_name == "search_agri_knowledge":
        chunks = data.get("chunks") or []
        docs = ", ".join(str(c.get("source_doc", "")) for c in chunks[:2])
        return f"[{tool_name}: hits={len(chunks)}, sources={docs}]"
    if tool_name in ("navigate_screen", "open_screen"):
        return f"[{tool_name}: target={data.get('target_screen')}]"
    return f"[{tool_name}: ok]"


class SessionMemoryStore:
    """Manages bounded per-session conversation history in Redis DB 2."""

    def __init__(
        self,
        redis_client: Optional[Any] = None,
        *,
        redis_url: Optional[str] = None,
        ttl_seconds: Optional[int] = None,
        max_turns: Optional[int] = None,
    ) -> None:
        self._redis = redis_client
        self._redis_url = redis_url or settings.AGENT_MEMORY_REDIS_URL
        self.ttl_seconds = ttl_seconds or settings.AGENT_MEMORY_TTL_SECONDS
        self.max_turns = max_turns or settings.AGENT_MEMORY_MAX_TURNS

    def _client(self) -> Any:
        if self._redis is None:
            self._redis = aioredis.from_url(self._redis_url, decode_responses=True)
        return self._redis

    @staticmethod
    def key(session_id: str) -> str:
        return f"{MEMORY_KEY_PREFIX}{session_id}"

    async def load_turns(self, session_id: str) -> list[MemoryTurn]:
        try:
            raw = await self._client().get(self.key(session_id))
        except (RedisError, OSError) as exc:
            logger.warning("Redis memory read failed for %s: %s", session_id, exc)
            return []
        if not raw:
            return []
        try:
            items = json.loads(raw)
            if not isinstance(items, list):
                return []
            return [MemoryTurn.from_dict(item) for item in items[-self.max_turns :] if isinstance(item, dict)]
        except (json.JSONDecodeError, TypeError):
            return []

    async def append_turn(
        self,
        session_id: str,
        *,
        user_text: str,
        assistant_text: str,
        intent: str = "",
        tool_summaries: Optional[list[str]] = None,
    ) -> None:
        turns = await self.load_turns(session_id)
        turns.append(
            MemoryTurn(
                user=user_text,
                assistant=assistant_text,
                intent=intent,
                tool_summaries=list(tool_summaries or []),
            )
        )
        trimmed = turns[-self.max_turns :]
        payload = json.dumps([t.to_dict() for t in trimmed], ensure_ascii=False)
        try:
            await self._client().set(self.key(session_id), payload, ex=self.ttl_seconds)
        except (RedisError, OSError) as exc:
            logger.warning("Redis memory write failed for %s: %s", session_id, exc)

    async def clear_session(self, session_id: str) -> bool:
        try:
            deleted = await self._client().delete(self.key(session_id))
            return bool(deleted)
        except (RedisError, OSError) as exc:
            logger.warning("Redis memory clear failed for %s: %s", session_id, exc)
            return False

    @staticmethod
    def to_messages(turns: list[MemoryTurn]) -> list[dict[str, str]]:
        messages: list[dict[str, str]] = []
        for turn in turns:
            if turn.user:
                messages.append({"role": "user", "content": turn.user})
            assistant_parts = []
            if turn.tool_summaries:
                assistant_parts.append(" ".join(turn.tool_summaries))
            if turn.assistant:
                assistant_parts.append(turn.assistant)
            if assistant_parts:
                messages.append({"role": "assistant", "content": "\n".join(assistant_parts)})
        return messages


__all__ = [
    "MEMORY_KEY_PREFIX",
    "MemoryTurn",
    "SessionMemoryStore",
    "compact_tool_summary",
]
