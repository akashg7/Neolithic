"""
Generate mock price forecasts for all seeded mandis and common crops.
Run: python scripts/generate_forecasts.py

NOTE: This generates mock data using the price engine stub.
Replace with real forecast generation once trained models are integrated.
"""
import asyncio
from datetime import datetime, timedelta

from sqlalchemy.ext.asyncio import create_async_engine, AsyncSession, async_sessionmaker
from sqlalchemy import select

import sys
sys.path.insert(0, ".")

from app.config import settings
from app.models.mandi import MandiLocation, PriceForecast
from app.engines.price_engine import price_engine


COMMODITIES = ["wheat", "rice", "onion", "potato", "tomato", "soybean"]


async def generate():
    engine = create_async_engine(settings.DATABASE_URL)
    session_factory = async_sessionmaker(engine, class_=AsyncSession, expire_on_commit=False)

    # Initialize price engine
    price_engine.load_models()

    async with session_factory() as db:
        # Get all mandis
        result = await db.execute(select(MandiLocation))
        mandis = result.scalars().all()

        if not mandis:
            print("No mandis found. Run seed_data.py first.")
            return

        count = 0
        for mandi in mandis:
            for commodity in COMMODITIES:
                forecasts = price_engine.predict_range(mandi.name, commodity, days=14)
                for fc in forecasts:
                    forecast = PriceForecast(
                        mandi=mandi.name,
                        commodity=commodity,
                        date=datetime.strptime(fc["date"], "%Y-%m-%d"),
                        p10_paise=fc["p10_paise"],
                        p50_paise=fc["p50_paise"],
                        p90_paise=fc["p90_paise"],
                        forecast_confidence=fc["confidence"],
                    )
                    db.add(forecast)
                    count += 1

        await db.commit()
        print(f"✅ Generated {count} price forecasts for {len(mandis)} mandis × {len(COMMODITIES)} commodities × 14 days")


if __name__ == "__main__":
    asyncio.run(generate())
