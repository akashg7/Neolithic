"""
Seed script — populates the database with real Maharashtra demo & reference data for testing.
Run: python scripts/seed_data.py [--force]
"""
import asyncio
import sys
from sqlalchemy.ext.asyncio import create_async_engine, AsyncSession, async_sessionmaker
from sqlalchemy import select, text

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

# All 36 Districts of Maharashtra
MAHARASHTRA_DISTRICTS = [
    {"id": 1, "name": "Nashik", "name_mr": "नाशिक"},
    {"id": 2, "name": "Pune", "name_mr": "पुणे"},
    {"id": 3, "name": "Ahmednagar", "name_mr": "अहिल्यानगर"},
    {"id": 4, "name": "Nagpur", "name_mr": "नागपूर"},
    {"id": 5, "name": "Solapur", "name_mr": "सोलापूर"},
    {"id": 6, "name": "Chhatrapati Sambhajinagar", "name_mr": "छत्रपती संभाजीनगर"},
    {"id": 7, "name": "Amravati", "name_mr": "अमरावती"},
    {"id": 8, "name": "Kolhapur", "name_mr": "कोल्हापूर"},
    {"id": 9, "name": "Satara", "name_mr": "सातारा"},
    {"id": 10, "name": "Sangli", "name_mr": "सांगली"},
    {"id": 11, "name": "Jalgaon", "name_mr": "जळगाव"},
    {"id": 12, "name": "Latur", "name_mr": "लातूर"},
    {"id": 13, "name": "Nanded", "name_mr": "नांदेड"},
    {"id": 14, "name": "Mumbai City", "name_mr": "मुंबई शहर"},
    {"id": 15, "name": "Mumbai Suburban", "name_mr": "मुंबई उपनगर"},
    {"id": 16, "name": "Thane", "name_mr": "ठाणे"},
    {"id": 17, "name": "Palghar", "name_mr": "पालघर"},
    {"id": 18, "name": "Buldhana", "name_mr": "बुलढाणा"},
    {"id": 19, "name": "Yavatmal", "name_mr": "यवतमाळ"},
    {"id": 20, "name": "Akola", "name_mr": "अकोला"},
    {"id": 21, "name": "Wardha", "name_mr": "वर्धा"},
    {"id": 22, "name": "Chandrapur", "name_mr": "चंद्रपूर"},
    {"id": 23, "name": "Beed", "name_mr": "बीड"},
    {"id": 24, "name": "Dharashiv", "name_mr": "धाराशिव"},
    {"id": 25, "name": "Parbhani", "name_mr": "परभणी"},
    {"id": 26, "name": "Jalna", "name_mr": "जालना"},
    {"id": 27, "name": "Dhule", "name_mr": "धुळे"},
    {"id": 28, "name": "Nandurbar", "name_mr": "नंदुरबार"},
    {"id": 29, "name": "Raigad", "name_mr": "रायगड"},
    {"id": 30, "name": "Ratnagiri", "name_mr": "रत्नागिरी"},
    {"id": 31, "name": "Sindhudurg", "name_mr": "सिंधुदुर्ग"},
    {"id": 32, "name": "Bhandara", "name_mr": "भंडारा"},
    {"id": 33, "name": "Gondia", "name_mr": "गोंदिया"},
    {"id": 34, "name": "Gadchiroli", "name_mr": "गडचिरोली"},
    {"id": 35, "name": "Hingoli", "name_mr": "हिंगोली"},
    {"id": 36, "name": "Washim", "name_mr": "वाशीम"},
]

# Major Maharashtra agricultural commodities
MAHARASHTRA_COMMODITIES = [
    {"id": 1, "name": "Onion", "name_mr": "कांदा", "storable_days": 120},
    {"id": 2, "name": "Soyabean", "name_mr": "सोयाबीन", "storable_days": 365},
    {"id": 3, "name": "Wheat", "name_mr": "गहू", "storable_days": 365},
    {"id": 4, "name": "Tomato", "name_mr": "टोमॅटो", "storable_days": 14},
    {"id": 5, "name": "Cotton", "name_mr": "कापूस", "storable_days": 270},
    {"id": 6, "name": "Potato", "name_mr": "बटाटा", "storable_days": 180},
    {"id": 7, "name": "Bengal Gram", "name_mr": "हरभरा", "storable_days": 365},
    {"id": 8, "name": "Green Chilli", "name_mr": "हिरवी मिरची", "storable_days": 10},
    {"id": 9, "name": "Banana", "name_mr": "केळी", "storable_days": 14},
    {"id": 10, "name": "Maize", "name_mr": "मका", "storable_days": 365},
    {"id": 11, "name": "Rice", "name_mr": "तांदूळ", "storable_days": 365},
    {"id": 12, "name": "Groundnut", "name_mr": "भुईमूग", "storable_days": 240},
    {"id": 13, "name": "Jowar", "name_mr": "ज्वारी", "storable_days": 365},
    {"id": 14, "name": "Turmeric", "name_mr": "हळद", "storable_days": 730},
]

# Real Maharashtra APMC Mandis (matching SOTA trained model names)
MAHARASHTRA_MANDIS = [
    {"id": 1, "name": "Lasalgaon APMC", "name_mr": "लासलगाव कृषी उत्पन्न बाजार समिती", "district_id": 1, "lat": 20.1438, "lng": 74.2386},
    {"id": 2, "name": "Nashik APMC", "name_mr": "नाशिक कृषी उत्पन्न बाजार समिती", "district_id": 1, "lat": 19.9975, "lng": 73.7898},
    {"id": 3, "name": "Pune APMC", "name_mr": "पुणे कृषी उत्पन्न बाजार समिती (गुलटेकडी)", "district_id": 2, "lat": 18.4967, "lng": 73.8647},
    {"id": 4, "name": "Pune(Moshi) APMC", "name_mr": "पुणे (मोशी) कृषी उत्पन्न बाजार समिती", "district_id": 2, "lat": 18.6756, "lng": 73.8441},
    {"id": 5, "name": "Ahilyanagar APMC", "name_mr": "अहिल्यानगर बाजार समिती", "district_id": 3, "lat": 19.0952, "lng": 74.7496},
    {"id": 6, "name": "Nagpur APMC", "name_mr": "नागपूर कृषी उत्पन्न बाजार समिती (कळमना)", "district_id": 4, "lat": 21.1738, "lng": 79.1482},
    {"id": 7, "name": "Solapur APMC", "name_mr": "सोलापूर कृषी उत्पन्न बाजार समिती", "district_id": 5, "lat": 17.6599, "lng": 75.9064},
    {"id": 8, "name": "Chattrapati Sambhajinagar APMC", "name_mr": "छत्रपती संभाजीनगर बाजार समिती (जाधववाडी)", "district_id": 6, "lat": 19.8975, "lng": 75.3524},
    {"id": 9, "name": "Amravati APMC", "name_mr": "अमरावती कृषी उत्पन्न बाजार समिती", "district_id": 7, "lat": 20.9374, "lng": 77.7796},
    {"id": 10, "name": "Kolhapur APMC", "name_mr": "कोल्हापूर कृषी उत्पन्न बाजार समिती (शाहुपुरी)", "district_id": 8, "lat": 16.7050, "lng": 74.2433},
    {"id": 11, "name": "Sangli APMC", "name_mr": "सांगली हळद व शेतीमाल बाजार समिती", "district_id": 10, "lat": 16.8524, "lng": 74.5815},
    {"id": 12, "name": "Jalgaon APMC", "name_mr": "जळगाव कृषी उत्पन्न बाजार समिती", "district_id": 11, "lat": 21.0077, "lng": 75.5626},
    {"id": 13, "name": "Latur APMC", "name_mr": "लातूर सोयाबीन व कडधान्य बाजार समिती", "district_id": 12, "lat": 18.4088, "lng": 76.5604},
    {"id": 14, "name": "Vashi APMC", "name_mr": "वाशी मुंबई कृषी उत्पन्न बाजार समिती", "district_id": 15, "lat": 19.0760, "lng": 72.9987},
]

# Real Maharashtra MSWC & WDRA Registered Warehouses
MAHARASHTRA_WAREHOUSES = [
    {"id": 1, "name": "MSWC Lasalgaon Onion Godown", "name_mr": "महाराष्ट्र राज्य वखार महामंडळ लासलगाव", "district_id": 1, "wdra_registered": True, "rent_paise_per_qtl_month": 4500, "source": "WDRA/MSWC"},
    {"id": 2, "name": "Sahyadri Agro Cold Chain", "name_mr": "सह्याद्री ॲग्रो कोल्ड स्टोरेज नाशिक", "district_id": 1, "wdra_registered": True, "rent_paise_per_qtl_month": 9000, "source": "WDRA/Private"},
    {"id": 3, "name": "MSWC Gultekdi Central Storage", "name_mr": "महाराष्ट्र राज्य वखार महामंडळ गुलटेकडी पुणे", "district_id": 2, "wdra_registered": True, "rent_paise_per_qtl_month": 5000, "source": "WDRA/MSWC"},
    {"id": 4, "name": "MSWC Kalamna Agri Logistics Godown", "name_mr": "महाराष्ट्र राज्य वखार महामंडळ कळमना नागपूर", "district_id": 4, "wdra_registered": True, "rent_paise_per_qtl_month": 4800, "source": "WDRA/MSWC"},
    {"id": 5, "name": "Solapur Regional Pulse Warehouse", "name_mr": "सोलापूर प्रादेशिक डाळ व कडधान्य गोदाम", "district_id": 5, "wdra_registered": True, "rent_paise_per_qtl_month": 4600, "source": "WDRA/MSWC"},
    {"id": 6, "name": "APMC Central Cold Storage Vashi", "name_mr": "वाशी सेंट्रल कोल्ड स्टोरेज नवी मुंबई", "district_id": 15, "wdra_registered": True, "rent_paise_per_qtl_month": 9500, "source": "WDRA/APMC"},
]

MAHARASHTRA_LOGISTICS = [
    {"name": "Maharashtra Agro Transport (Nashik Hub)", "type": "transport", "lat": 20.00, "lng": 73.80, "capacity_kg": 25000, "contact": "9822012345"},
    {"name": "Sahyadri Cold Express (Reefer Fleet)", "type": "storage", "lat": 20.14, "lng": 74.23, "capacity_kg": 50000, "contact": "9822098765"},
    {"name": "Pune Agri Cargo Operators", "type": "transport", "lat": 18.52, "lng": 73.85, "capacity_kg": 40000, "contact": "9823054321"},
    {"name": "Vidarbha Farm Logistics (Nagpur)", "type": "transport", "lat": 21.15, "lng": 79.10, "capacity_kg": 30000, "contact": "9824011223"},
]

DEMO_FPOS = [
    {"id": 1, "name": "Sahyadri Farmers Producer Co. Ltd.", "region": "Maharashtra (Nashik)"},
    {"id": 2, "name": "MahaAgri FPO Consortium", "region": "Maharashtra (Pune)"},
]

async def seed():
    force = "--force" in sys.argv
    engine = create_async_engine(settings.DATABASE_URL)
    session_factory = async_sessionmaker(engine, class_=AsyncSession, expire_on_commit=False)

    async with session_factory() as db:
        # Check existing data
        result = await db.execute(select(District).limit(1))
        existing_district = result.scalar_one_or_none()

        if existing_district and not force:
            print("Database already contains seed data. Run with --force to overwrite. Skipping.")
            return

        if force:
            print("Force flag set — wiping reference tables before seeding...")
            await db.execute(text("DELETE FROM offer_lots;"))
            await db.execute(text("DELETE FROM offers;"))
            await db.execute(text("DELETE FROM lots;"))
            await db.execute(text("DELETE FROM buyer_demand;"))
            await db.execute(text("DELETE FROM farmers;"))
            await db.execute(text("DELETE FROM buyers;"))
            await db.execute(text("DELETE FROM users WHERE id IN (1, 2, 3);"))
            await db.execute(text("DELETE FROM logistics_providers;"))
            await db.execute(text("DELETE FROM warehouses;"))
            await db.execute(text("DELETE FROM mandi_locations;"))
            await db.execute(text("DELETE FROM commodities;"))
            await db.execute(text("DELETE FROM fpos;"))
            await db.execute(text("DELETE FROM districts;"))
            await db.commit()

        print("Seeding Maharashtra Districts (36)...")
        for d in MAHARASHTRA_DISTRICTS:
            db.add(District(**d))
        await db.flush()

        print("Seeding Maharashtra Commodities (14)...")
        for c in MAHARASHTRA_COMMODITIES:
            db.add(Commodity(**c))
        await db.flush()

        print("Seeding Maharashtra APMC Mandis (14)...")
        for m in MAHARASHTRA_MANDIS:
            db.add(MandiLocation(**m))
        await db.flush()

        print("Seeding Maharashtra WDRA Warehouses (6)...")
        for w in MAHARASHTRA_WAREHOUSES:
            db.add(Warehouse(**w))
        await db.flush()

        print("Seeding Maharashtra FPOs (2)...")
        for f in DEMO_FPOS:
            db.add(FPO(**f))
        await db.flush()

        print("Seeding Maharashtra Logistics Providers (4)...")
        for lp in MAHARASHTRA_LOGISTICS:
            db.add(LogisticsProvider(**lp, source="demo"))
        await db.flush()

        print("Seeding Demo Maharashtra Users & Profiles...")
        # 1. Farmer: Ramesh Patil (Nashik)
        farmer_user = User(
            id=1,
            name="Ramesh Patil (शेतकरी)",
            phone="9822011111",
            role="FARMER",
            district_id=1, # Nashik
            village="Lasalgaon",
            locale="mr",
        )
        db.add(farmer_user)
        db.add(Farmer(user_id=1, fpo_id=1))

        # 2. Buyer: Reliance Retail Agri Sourcing (Mumbai/Vashi)
        buyer_user = User(
            id=2,
            name="Reliance Fresh Sourcing",
            phone="9822022222",
            role="BUYER",
            district_id=15, # Mumbai
            locale="en",
        )
        db.add(buyer_user)
        db.add(Buyer(user_id=2, company_name="Reliance Fresh Agri Ltd.", verified_status=True))

        # 3. FPO Admin
        fpo_admin = User(
            id=3,
            name="Sahyadri FPO Manager",
            phone="9822033333",
            role="FPO_ADMIN",
            district_id=1,
            locale="mr",
        )
        db.add(fpo_admin)
        await db.flush()

        print("Seeding Active Maharashtra Demand & Lot...")
        # Institutional demand for Grade A Onion in Nashik/Mumbai
        demand = BuyerDemand(
            id=1,
            buyer_id=2,
            commodity_id=1, # Onion
            market_id=1,    # Lasalgaon
            quantity_qtl=500,
            expected_price_paise=240000, # ₹2400/qtl
            desired_grade="A",
        )
        db.add(demand)

        # Farmer Lot: 50 Quintals of Nashik Onion
        lot = Lot(
            id=1,
            farmer_id=1,
            fpo_id=1,
            commodity_id=1, # Onion
            market_id=1,    # Lasalgaon APMC
            quantity_qtl=50,
            expected_price_paise=235000, # ₹2350/qtl
            grade="A",
        )
        db.add(lot)
        await db.flush()

        # Buyer Offer
        offer = Offer(
            id=1,
            demand_id=1,
            buyer_id=2,
            farmer_id=1,
            price_paise_per_qtl=238000, # ₹2380/qtl
            qty_kg=5000, # 50 qtl
            round=1,
            initiator="BUYER",
            status="OPEN",
        )
        db.add(offer)
        await db.flush()

        offer_lot = OfferLot(
            offer_id=1,
            lot_id=1,
            quantity_allocated_kg=5000,
        )
        db.add(offer_lot)

        await db.commit()
        print("✅ Maharashtra seed data populated successfully!")

if __name__ == "__main__":
    asyncio.run(seed())
