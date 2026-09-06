import asyncio
from sqlalchemy.ext.asyncio import create_async_engine
import sys
sys.path.insert(0, ".")

from app.config import settings
from app.database import Base

# Import all models to register them with Base.metadata
from app.models.user import User, Farmer, Buyer
from app.models.mandi import MandiLocation, PriceForecast, PriceObservation
from app.models.reference import District, Commodity, Warehouse, LogisticsCostRoute
from app.models.logistics import LogisticsProvider
from app.models.fpo import FPO
from app.models.demand import BuyerDemand
from app.models.lot import Lot
from app.models.offer import Offer
from app.models.transaction import Transaction, EscrowEvent

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
