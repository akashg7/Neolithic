"""
Seed script — populates the database with demo data for testing.
Run: python scripts/seed_data.py
"""
import asyncio
from sqlalchemy.ext.asyncio import create_async_engine, AsyncSession, async_sessionmaker
from sqlalchemy import select

# Must be run from project root
import sys
sys.path.insert(0, ".")

from app.config import settings
from app.database import Base
from app.models.mandi import MandiLocation
from app.models.logistics import LogisticsProvider
from app.models.demand import BuyerDemand
from app.models.fpo import FPO
from app.models.user import User, Buyer


MANDI_LOCATIONS = [
    {"name": "Azadpur Mandi", "district": "Delhi", "lat": 28.7041, "lng": 77.1025},
    {"name": "Vashi APMC", "district": "Mumbai", "lat": 19.0760, "lng": 72.9987},
    {"name": "Koyambedu Market", "district": "Chennai", "lat": 13.0694, "lng": 80.1948},
    {"name": "Bowenpally Market", "district": "Hyderabad", "lat": 17.4611, "lng": 78.4697},
    {"name": "Yeshwanthpur APMC", "district": "Bangalore", "lat": 13.0228, "lng": 77.5439},
    {"name": "Devi Ahilya Bai Mandi", "district": "Indore", "lat": 22.7196, "lng": 75.8577},
    {"name": "Sahukara Mandi", "district": "Jaipur", "lat": 26.9157, "lng": 75.8018},
    {"name": "Lasalgaon APMC", "district": "Nashik", "lat": 20.1438, "lng": 74.2386},
    {"name": "Karnal Grain Market", "district": "Karnal", "lat": 29.6857, "lng": 76.9905},
    {"name": "Guntur Mirchi Yard", "district": "Guntur", "lat": 16.3067, "lng": 80.4365},
    {"name": "Rajkot APMC", "district": "Rajkot", "lat": 22.3039, "lng": 70.8022},
    {"name": "Unjha APMC", "district": "Mehsana", "lat": 23.7956, "lng": 72.3917},
]

LOGISTICS_PROVIDERS = [
    {"name": "ColdStore Delhi Pvt Ltd", "type": "storage", "lat": 28.68, "lng": 77.12, "capacity_kg": 50000, "contact": "9876543210"},
    {"name": "Delhi Fresh Transport", "type": "transport", "lat": 28.71, "lng": 77.08, "capacity_kg": 10000, "contact": "9876543211"},
    {"name": "Vashi Cold Chain Solutions", "type": "storage", "lat": 19.08, "lng": 73.00, "capacity_kg": 80000, "contact": "9876543212"},
    {"name": "Mumbai Agri Transport", "type": "transport", "lat": 19.05, "lng": 72.95, "capacity_kg": 15000, "contact": "9876543213"},
    {"name": "Karnal Grain Storage", "type": "storage", "lat": 29.70, "lng": 76.98, "capacity_kg": 100000, "contact": "9876543214"},
    {"name": "Punjab Transport Services", "type": "transport", "lat": 29.65, "lng": 76.95, "capacity_kg": 20000, "contact": "9876543215"},
    {"name": "Jaipur Agri Warehouse", "type": "storage", "lat": 26.90, "lng": 75.80, "capacity_kg": 60000, "contact": "9876543216"},
    {"name": "Rajasthan Truck Fleet", "type": "transport", "lat": 26.92, "lng": 75.82, "capacity_kg": 25000, "contact": "9876543217"},
]

DEMO_DEMANDS = [
    {"buyer_id": 1, "crop": "wheat", "desired_qty_kg": 2000, "desired_grade": "A", "max_price_paise_per_qtl": 220000, "lat": 28.63, "lng": 77.22, "source": "demo"},
    {"buyer_id": 1, "crop": "rice", "desired_qty_kg": 5000, "desired_grade": "B", "max_price_paise_per_qtl": 260000, "lat": 19.07, "lng": 72.87, "source": "demo"},
    {"buyer_id": 1, "crop": "onion", "desired_qty_kg": 1000, "desired_grade": None, "max_price_paise_per_qtl": 190000, "lat": 20.14, "lng": 74.23, "source": "demo"},
    {"buyer_id": 1, "crop": "soybean", "desired_qty_kg": 3000, "desired_grade": "A", "max_price_paise_per_qtl": 400000, "lat": 22.72, "lng": 75.86, "source": "demo"},
    {"buyer_id": 1, "crop": "wheat", "desired_qty_kg": 10000, "desired_grade": "B", "max_price_paise_per_qtl": 215000, "lat": 29.68, "lng": 76.99, "source": "demo"},
]

DEMO_FPOS = [
    {"name": "Kisan Pragati FPO", "region": "Haryana"},
    {"name": "Sahyadri Farmers FPO", "region": "Maharashtra"},
    {"name": "Green Valley FPO", "region": "Rajasthan"},
]


async def seed():
    engine = create_async_engine(settings.DATABASE_URL)
    session_factory = async_sessionmaker(engine, class_=AsyncSession, expire_on_commit=False)

    async with session_factory() as db:
        # Check if already seeded
        result = await db.execute(select(MandiLocation).limit(1))
        if result.scalar_one_or_none():
            print("Database already seeded. Skipping.")
            return

        # Seed FPOs
        for fpo_data in DEMO_FPOS:
            db.add(FPO(**fpo_data))
        print(f"Seeded {len(DEMO_FPOS)} FPOs")

        # Seed Mandi Locations
        for mandi_data in MANDI_LOCATIONS:
            db.add(MandiLocation(**mandi_data))
        print(f"Seeded {len(MANDI_LOCATIONS)} mandi locations")

        # Seed Logistics Providers
        for provider_data in LOGISTICS_PROVIDERS:
            db.add(LogisticsProvider(**provider_data, source="demo"))
        print(f"Seeded {len(LOGISTICS_PROVIDERS)} logistics providers")

        # Seed Demo Demands (buyer_id=1 is placeholder — update after a buyer registers)
        # Create the placeholder buyer first
        buyer_check = await db.execute(select(User).where(User.id == 1))
        if not buyer_check.scalar_one_or_none():
            buyer_user = User(
                id=1,
                name="Demo Buyer",
                phone="1234567890",
                password_hash="hashed",
                role="buyer",
                preferred_language="en",
            )
            db.add(buyer_user)
            db.add(Buyer(user_id=1, company_name="Demo Company"))
            await db.flush()

        for demand_data in DEMO_DEMANDS:
            db.add(BuyerDemand(**demand_data))
        print(f"Seeded {len(DEMO_DEMANDS)} demo buyer demands")

        await db.commit()
        print("\n✅ Seed data complete!")


if __name__ == "__main__":
    asyncio.run(seed())
