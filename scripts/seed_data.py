"""
Seed script — populates the database with demo data for testing.
Run: python scripts/seed_data.py
"""
import asyncio
from sqlalchemy.ext.asyncio import create_async_engine, AsyncSession, async_sessionmaker
from sqlalchemy import select

import sys
sys.path.insert(0, ".")

from app.config import settings
from app.database import Base
from app.models.reference import District, Commodity, Warehouse
from app.models.mandi import MandiLocation
from app.models.logistics import LogisticsProvider
from app.models.fpo import FPO
from app.models.user import User, Buyer, Farmer
from app.models.demand import BuyerDemand
from app.models.lot import Lot
from app.models.offer import Offer, OfferLot


DISTRICTS = [
    {"id": 1, "name": "Delhi", "name_mr": "दिल्ली"},
    {"id": 2, "name": "Mumbai", "name_mr": "मुंबई"},
    {"id": 3, "name": "Nashik", "name_mr": "नाशिक"},
    {"id": 4, "name": "Karnal", "name_mr": "करनाल"},
    {"id": 5, "name": "Indore", "name_mr": "इंदूर"},
]

COMMODITIES = [
    {"id": 1, "name": "wheat", "name_mr": "गहू", "storable_days": 365},
    {"id": 2, "name": "onion", "name_mr": "कांदा", "storable_days": 180},
    {"id": 3, "name": "soybean", "name_mr": "सोयाबीन", "storable_days": 365},
]

WAREHOUSES = [
    {"id": 1, "name": "Central Storage", "name_mr": "मध्यवर्ती साठवण", "district_id": 3, "wdra_registered": True, "rent_paise_per_qtl_month": 5000, "source": "demo"}
]

MANDI_LOCATIONS = [
    {"id": 1, "name": "Azadpur Mandi", "name_mr": "आझादपूर मंडी", "district_id": 1, "lat": 28.7041, "lng": 77.1025},
    {"id": 2, "name": "Vashi APMC", "name_mr": "वाशी कृषी उत्पन्न बाजार समिती", "district_id": 2, "lat": 19.0760, "lng": 72.9987},
    {"id": 3, "name": "Lasalgaon APMC", "name_mr": "लासलगाव कृषी उत्पन्न बाजार समिती", "district_id": 3, "lat": 20.1438, "lng": 74.2386},
]

LOGISTICS_PROVIDERS = [
    {"name": "ColdStore Delhi Pvt Ltd", "type": "storage", "lat": 28.68, "lng": 77.12, "capacity_kg": 50000, "contact": "9876543210"},
]

DEMO_FPOS = [
    {"id": 1, "name": "Sahyadri Farmers FPO", "region": "Maharashtra"},
]

async def seed():
    engine = create_async_engine(settings.DATABASE_URL)
    session_factory = async_sessionmaker(engine, class_=AsyncSession, expire_on_commit=False)

    async with session_factory() as db:
        # Check if already seeded
        result = await db.execute(select(District).limit(1))
        if result.scalar_one_or_none():
            print("Database already seeded. Skipping.")
            return

        # Districts
        for d in DISTRICTS:
            db.add(District(**d))
        await db.flush()
        
        # Commodities
        for c in COMMODITIES:
            db.add(Commodity(**c))
        await db.flush()

        # Warehouses
        for w in WAREHOUSES:
            db.add(Warehouse(**w))
        await db.flush()

        # FPOs
        for f in DEMO_FPOS:
            db.add(FPO(**f))
        await db.flush()
            
        # Mandis
        for m in MANDI_LOCATIONS:
            db.add(MandiLocation(**m))
        await db.flush()

        # Logistics
        for lp in LOGISTICS_PROVIDERS:
            db.add(LogisticsProvider(**lp, source="demo"))
        await db.flush()

        # Users
        farmer_user = User(
            id=1,
            name="Ramesh Kumar (Demo Farmer)",
            phone="9999999999",
            role="FARMER",
            district_id=3,
        )
        db.add(farmer_user)
        db.add(Farmer(user_id=1, fpo_id=1))

        buyer_user = User(
            id=2,
            name="Acme Corp (Demo Buyer)",
            phone="8888888888",
            role="BUYER",
            district_id=2,
        )
        db.add(buyer_user)
        db.add(Buyer(user_id=2, company_name="Acme Corp", verified_status=True))

        await db.flush()

        # Buyer Demand
        demand = BuyerDemand(
            id=1,
            buyer_id=2,
            commodity_id=1, # wheat
            market_id=2,
            quantity_qtl=50,
            expected_price_paise=220000,
            desired_grade="A"
        )
        db.add(demand)

        # Lot
        lot = Lot(
            id=1,
            farmer_id=1,
            fpo_id=1,
            commodity_id=1, # wheat
            market_id=3,
            quantity_qtl=10,
            expected_price_paise=230000,
            grade="A"
        )
        db.add(lot)

        await db.flush()

        # Offer
        offer = Offer(
            id=1,
            demand_id=1,
            buyer_id=2,
            farmer_id=1,
            price_paise_per_qtl=225000,
            qty_kg=1000, # 10 qtl
            round=1,
            initiator="BUYER",
            status="OPEN"
        )
        db.add(offer)

        await db.flush()

        offer_lot = OfferLot(
            offer_id=1,
            lot_id=1,
            quantity_allocated_kg=1000
        )
        db.add(offer_lot)

        await db.commit()
        print("✅ Seed data complete!")

if __name__ == "__main__":
    asyncio.run(seed())
