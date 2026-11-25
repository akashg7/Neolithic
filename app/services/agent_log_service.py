"""Async fire-and-forget turn logger for `AgentTurnLog`.

Never raises or blocks a user turn; uses an isolated DB session so logging
failures or offline DB tests do not disturb `/agent/chat` or `/agent/voice-chat`.
"""
from __future__ import annotations

import asyncio
import logging
import statistics
from collections import Counter
from datetime import datetime, timedelta, timezone
from typing import Any, Optional

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

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


def compute_turn_metrics(rows: list[Any]) -> dict[str, Any]:
    """Aggregate intent, error, refusal, and p50/p95 latency metrics from turn rows."""
    intents: Counter[str] = Counter()
    errors: Counter[str] = Counter()
    channels: Counter[str] = Counter()
    locales: Counter[str] = Counter()
    latencies: list[int] = []
    text_latencies: list[int] = []
    voice_latencies: list[int] = []
    failures: list[dict[str, Any]] = []
    refusals = 0

    for r in rows:
        intent = getattr(r, "intent_detected", None) or "UNKNOWN"
        intents[intent] += 1
        ch = getattr(r, "channel", None) or "text"
        channels[ch] += 1
        loc = getattr(r, "locale", None) or "mr"
        locales[loc] += 1
        err = getattr(r, "error_code", None)
        if err:
            errors[err] += 1
            if err in ("NO_ADVICE", "CHEMICAL_ADVICE_REFUSED"):
                refusals += 1
            else:
                failures.append(
                    {
                        "turn_id": getattr(r, "turn_id", None),
                        "session_id": getattr(r, "session_id", None),
                        "locale": loc,
                        "intent": intent,
                        "error_code": err,
                        "latency_ms": getattr(r, "latency_ms", None),
                        "original_text": (getattr(r, "original_text", None) or "")[:120],
                    }
                )
        lat = getattr(r, "latency_ms", None)
        if isinstance(lat, (int, float)) and lat >= 0:
            v = int(lat)
            latencies.append(v)
            if ch == "voice":
                voice_latencies.append(v)
            else:
                text_latencies.append(v)

    def _lat_stats(xs: list[int]) -> dict[str, Optional[float]]:
        if not xs:
            return {"n": 0, "p50_ms": None, "p95_ms": None, "max_ms": None}
        s = sorted(xs)
        p95_idx = min(len(s) - 1, int(round(0.95 * (len(s) - 1))))
        return {
            "n": len(s),
            "p50_ms": round(float(statistics.median(s)), 1),
            "p95_ms": float(s[p95_idx]),
            "max_ms": float(s[-1]),
        }

    return {
        "total_turns": len(rows),
        "by_intent": dict(intents),
        "by_channel": dict(channels),
        "by_locale": dict(locales),
        "error_counts": dict(errors),
        "refusal_count": refusals,
        "latency_ms": {
            "overall": _lat_stats(latencies),
            "text": _lat_stats(text_latencies),
            "voice": _lat_stats(voice_latencies),
        },
        "recent_failures": failures[:20],
    }


async def summarize_turn_logs(
    db: Optional[AsyncSession],
    *,
    hours: int = 24,
    limit: int = 500,
) -> dict[str, Any]:
    """Read recent `AgentTurnLog` rows for Day 5 triage and latency analysis."""
    if db is None:
        return compute_turn_metrics([])
    try:
        since = datetime.now(timezone.utc) - timedelta(hours=max(1, hours))
        stmt = (
            select(AgentTurnLog)
            .where(AgentTurnLog.created_at >= since)
            .order_by(AgentTurnLog.created_at.desc())
            .limit(max(1, min(limit, 5000)))
        )
        rows = (await db.execute(stmt)).scalars().all()
        return compute_turn_metrics(list(rows))
    except Exception as exc:
        logger.warning("Failed to read AgentTurnLog metrics: %s", exc)
        return compute_turn_metrics([])


__all__ = [
    "compute_turn_metrics",
    "schedule_turn_log",
    "summarize_turn_logs",
    "write_agent_turn_log",
]
