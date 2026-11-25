"""Day 5 triage report from `agent_turns` (`AgentTurnLog`): intents, errors, p50/p95 latency."""
from __future__ import annotations

import argparse
import asyncio
import json
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))

from app.database import async_session  # noqa: E402
from app.services.agent_log_service import summarize_turn_logs  # noqa: E402


async def _run(hours: int, limit: int) -> dict:
    async with async_session() as db:
        return await summarize_turn_logs(db, hours=hours, limit=limit)


def main() -> None:
    ap = argparse.ArgumentParser(description="Inspect AgentTurnLog latency and failure metrics.")
    ap.add_argument("--hours", type=int, default=24)
    ap.add_argument("--limit", type=int, default=500)
    args = ap.parse_args()
    summary = asyncio.run(_run(args.hours, args.limit))
    print(json.dumps(summary, indent=2, ensure_ascii=False))


if __name__ == "__main__":
    main()
