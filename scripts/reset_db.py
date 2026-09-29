import asyncio
from sqlalchemy.ext.asyncio import create_async_engine
import sys
sys.path.insert(0, ".")

from app.config import settings
from app.database import Base

# Import all models to register them with Base.metadata
import app.models  # noqa: F401

from sqlalchemy import text

async def reset_database():
    engine = create_async_engine(settings.DATABASE_URL, echo=True)
    async with engine.begin() as conn:
        print("Dropping public schema cascade...")
        await conn.execute(text("DROP SCHEMA public CASCADE;"))
        await conn.execute(text("CREATE SCHEMA public;"))
        await conn.execute(text("CREATE EXTENSION IF NOT EXISTS postgis;"))
        print("Creating all tables...")
        await conn.run_sync(Base.metadata.create_all)
    
    print("Database reset complete.")
    await engine.dispose()

if __name__ == "__main__":
    asyncio.run(reset_database())
