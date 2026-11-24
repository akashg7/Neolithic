"""Container start-up: make sure the database is usable, then exit.

- Waits for Postgres to accept connections (compose healthchecks cover the
  normal case; this covers a slow volume mount or a restart race).
- Empty database (no `users` table) → build the schema and load the demo seed
  (`scripts.seed_demo`). This is what makes a first `docker compose up` on a
  fresh server come up with data, in one step.
- Existing database → leave it alone. Data in the `pgdata` volume survives
  rebuilds and redeploys. To reset to the demo story (e.g. demo morning, which
  also moves prices up to yesterday):
      docker compose exec api python -m scripts.seed_demo

`SEED_ON_EMPTY=false` skips the seed (schema is still created).
"""
from __future__ import annotations

import asyncio
import os
import sys

from sqlalchemy import text


async def _wait_for_db(engine, attempts: int = 60) -> None:
    for i in range(attempts):
        try:
            async with engine.connect() as conn:
                await conn.execute(text("SELECT 1"))
            return
        except Exception as exc:  # noqa: BLE001 — any failure means "not yet"
            if i == attempts - 1:
                sys.exit(f"bootstrap: database not reachable: {exc}")
            await asyncio.sleep(1)


async def main() -> None:
    from app.database import engine

    await _wait_for_db(engine)
    async with engine.connect() as conn:
        await conn.execute(text("CREATE EXTENSION IF NOT EXISTS postgis"))
        await conn.commit()
        has_users = (await conn.execute(text("SELECT to_regclass('public.users') IS NOT NULL"))).scalar()

    if has_users:
        print("bootstrap: database already initialised — keeping existing data")
        await engine.dispose()
        return

    from scripts import seed_demo

    print("bootstrap: empty database — building schema")
    await seed_demo.reset_schema()
    if os.getenv("SEED_ON_EMPTY", "true").lower() in ("1", "true", "yes"):
        print("bootstrap: loading demo seed")
        await seed_demo.seed(seed_demo.DEFAULT_CSV)
    await engine.dispose()


if __name__ == "__main__":
    asyncio.run(main())
