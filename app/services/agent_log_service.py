"""Async fire-and-forget turn logger for `AgentTurnLog`.

Never raises or blocks a user turn; uses an isolated DB session so logging
failures or offline DB tests do not disturb `/agent/chat` or `/agent/voice-chat`.
"""
from __future__ import annotations

import asyncio
import logging
from typing import Any, Optional

from app.database import async_session
from app.models.agent_turn import AgentTurnLog

logger = logging.getLogger("krishi.turn_log")

_PENDING_TASKS: set[asyncio.Task] = set()


async def write_agent_turn_log(
    *,
    turn_id: str,
    session_id: str,
    user_id: Optional[int] = None,
    locale: str = "mr",
    channel: str = "text",
    screen_context: Optional[dict[str, Any]] = None,
    original_text: Optional[str] = None,
    english_text: Optional[str] = None,
    transcript: Optional[str] = None,
    english_reply: Optional[str] = None,
    reply_text: Optional[str] = None,
    intent_detected: Optional[str] = None,
    tools_called: Optional[list[dict[str, Any]]] = None,
    rag_sources: Optional[list[dict[str, Any]]] = None,
    latency_ms: Optional[int] = None,
    error_code: Optional[str] = None,
) -> None:
    """Persist one `AgentTurnLog` row in its own DB session."""
    try:
        async with async_session() as session:
            row = AgentTurnLog(
                turn_id=turn_id,
                session_id=session_id,
                user_id=user_id,
                locale=locale,
                channel=channel,
                screen_context=screen_context,
                original_text=original_text,
                english_text=english_text,
                transcript=transcript if transcript is not None else original_text,
                english_reply=english_reply,
                reply_text=reply_text,
                intent_detected=intent_detected,
                tools_called=tools_called,
                rag_sources=rag_sources,
                latency_ms=latency_ms,
                error_code=error_code,
            )
            session.add(row)
            await session.commit()
    except Exception as exc:
        logger.debug("Async AgentTurnLog write skipped/failed for %s: %s", turn_id, exc)


def schedule_turn_log(**kwargs: Any) -> Optional[asyncio.Task]:
    """Fire-and-forget scheduling onto the running event loop."""
    try:
        loop = asyncio.get_running_loop()
    except RuntimeError:
        return None
    task = loop.create_task(write_agent_turn_log(**kwargs))
    _PENDING_TASKS.add(task)
    task.add_done_callback(_PENDING_TASKS.discard)
    return task


__all__ = ["schedule_turn_log", "write_agent_turn_log"]
