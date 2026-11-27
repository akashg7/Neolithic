"""Seed a complete, working demo database for Krishi-Mitr.

    python -m scripts.seed_demo                 # reset + seed (uses DATABASE_URL)
    python -m scripts.seed_demo --no-reset      # seed into an existing schema
    python -m scripts.seed_demo --csv path.csv  # a different Agmarknet export

What it creates
---------------
* Reference data whose ids match the app exactly (`cmd_onion`, `mkt_lasalgaon`,
  `dist_nashik`, ...): 19 districts, 14 crops, 34 mandis with coordinates.
* ~1 year of **real Agmarknet prices** for those crops × mandis, from
  `maharashtra/agmarknet_maharashtra_full_1year.csv` if present, else the committed
  extract `data/seed/agmarknet_maharashtra_demo.csv.gz` (same rows). The export ends on 2026-09-05, so every date is
  shifted forward by the same offset to end yesterday, and every row is stored
  with source **ARCHIVE** — the app badges it, nobody is told it is today's
  live feed. Price shapes, levels and seasonality are untouched.
* Demo people: farmer रामभाऊ पाटील (9822011111), two more Nashik farmers, two
  buyers (9822022222, 9822022223), an FPO admin (9822033333).
* A demo story: open lots, two competing offers on the onion lot, one deal in
  transit and one settled — each with its append-only escrow events.
* Warehouses (WDRA) and logistics providers, marked `source='demo'`.

Schema
------
Built from the SQLAlchemy models (the Alembic chain is behind the models), then
stamped at the Alembic head so `alembic upgrade head` on container start is a no-op.
"""

from __future__ import annotations

import argparse
import asyncio
import csv
import gzip
import os
import sys
from collections import defaultdict
from datetime import date, datetime, timedelta, timezone
from pathlib import Path

from geoalchemy2.elements import WKTElement
from sqlalchemy import text

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))

from app.database import Base, async_session, engine  # noqa: E402
import app.models  # noqa: E402,F401  (register every table)
from app.models.demand import BuyerDemand  # noqa: E402
from app.models.fpo import FPO  # noqa: E402
from app.models.logistics import LogisticsProvider  # noqa: E402
from app.models.lot import Lot  # noqa: E402
from app.models.mandi import MandiLocation, PriceObservation  # noqa: E402
from app.models.offer import Offer, OfferLot  # noqa: E402
from app.models.reference import Commodity, District, Warehouse  # noqa: E402
from app.models.transaction import EscrowEvent, Transaction  # noqa: E402
from app.models.user import Buyer, Farmer, User  # noqa: E402
from app.utils import id_resolver  # noqa: E402

ALEMBIC_HEAD = "003_agent_turns"
# Full export if present locally; otherwise the committed extract (same rows,
# only the app's crops × mandis, gzipped) so the seed also works on a fresh server.
_FULL_CSV = ROOT / "maharashtra" / "agmarknet_maharashtra_full_1year.csv"
_EXTRACT_CSV = ROOT / "data" / "seed" / "agmarknet_maharashtra_demo.csv.gz"
DEFAULT_CSV = _FULL_CSV if _FULL_CSV.exists() else _EXTRACT_CSV

# name, name_mr
DISTRICTS = [
    ("Nashik", "नाशिक"), ("Latur", "लातूर"), ("Ahmednagar", "अहिल्यानगर"), ("Pune", "पुणे"),
    ("Jalgaon", "जळगाव"), ("Solapur", "सोलापूर"), ("Chhatrapati Sambhajinagar", "छत्रपती संभाजीनगर"),
    ("Yavatmal", "यवतमाळ"), ("Wardha", "वर्धा"), ("Akola", "अकोला"), ("Nanded", "नांदेड"),
    ("Hingoli", "हिंगोली"), ("Parbhani", "परभणी"), ("Sangli", "सांगली"), ("Kolhapur", "कोल्हापूर"),
    ("Dhule", "धुळे"), ("Satara", "सातारा"), ("Mumbai", "मुंबई"), ("Beed", "बीड"),
]

# name, name_mr, storable_days, Agmarknet commodity names
COMMODITIES = [
    ("Onion", "कांदा", 150, ["Onion"]),
    ("Soyabean", "सोयाबीन", 180, ["Soyabean"]),
    ("Cotton", "कापूस", 210, ["Cotton"]),
    ("Tomato", "टोमॅटो", 7, ["Tomato"]),
    ("Wheat", "गहू", 360, ["Wheat"]),
    ("Bengal Gram", "हरभरा", 240, ["Bengal Gram(Gram)(Whole)"]),
    ("Maize", "मका", 180, ["Maize"]),
    ("Green Chilli", "हिरवी मिरची", 10, ["Green Chilli"]),
    ("Turmeric", "हळद", 365, ["Turmeric"]),
    ("Groundnut", "भुईमूग", 240, ["Groundnut"]),
    ("Pomegranate", "डाळिंब", 30, ["Pomegranate"]),
    ("Grapes", "द्राक्षे", 20, ["Grapes"]),
    ("Potato", "बटाटा", 120, ["Potato"]),
    ("Red Gram (Tur)", "तूर", 300, ["Red gram/Arhar/Tur(whole)"]),
]

# name, name_mr, district, lat, lng, Agmarknet mandi names
MARKETS = [
    ("Lasalgaon APMC", "लासलगाव", "Nashik", 20.1438, 74.2386, ["APMC Lasalgaon", "Lasalgaon(Niphad)", "Lasalgaon(Vinchur)"]),
    ("Pimpalgaon Baswant APMC", "पिंपळगाव बसवंत", "Nashik", 20.1667, 73.9881, ["APMC Pimpalgaon Baswant", "Pimpalgaon Baswant(Saykheda)"]),
    ("Yeola APMC", "येवला", "Nashik", 20.0420, 74.4890, ["APMC Yeola"]),
    ("Nashik APMC", "नाशिक", "Nashik", 19.9975, 73.7898, ["Nashik(Devlali)", "Premium Krushi Utpanna Bazar, Nashik"]),
    ("Malegaon APMC", "मालेगाव", "Nashik", 20.5537, 74.5288, ["APMC Malegaon"]),
    ("Latur APMC", "लातूर", "Latur", 18.4088, 76.5604, ["APMC  Latur", "Latur(Murud)"]),
    ("Udgir APMC", "उदगीर", "Latur", 18.3920, 77.1160, ["APMC Udgir"]),
    ("Ahilyanagar APMC", "अहिल्यानगर", "Ahmednagar", 19.0952, 74.7496, ["APMC Ahilyanagar"]),
    ("Kopargaon APMC", "कोपरगाव", "Ahmednagar", 19.8830, 74.4770, ["APMC Kopargaon"]),
    ("Rahata APMC", "राहाता", "Ahmednagar", 19.7130, 74.4830, ["APMC Rahata"]),
    ("Pune APMC", "पुणे (गुलटेकडी)", "Pune", 18.4967, 73.8647, ["APMC Pune"]),
    ("Pune(Moshi) APMC", "पुणे (मोशी)", "Pune", 18.6756, 73.8441, ["Pune(Moshi)"]),
    ("Junnar (Narayangaon) APMC", "जुन्नर (नारायणगाव)", "Pune", 19.1167, 73.9667, ["Junnar(Narayangaon)", "APMC Junnar", "Junnar(Otur)"]),
    ("Baramati APMC", "बारामती", "Pune", 18.1517, 74.5770, ["APMC Baramati"]),
    ("Manchar APMC", "मंचर", "Pune", 19.0050, 73.9440, ["APMC Manchar"]),
    ("Jalgaon APMC", "जळगाव", "Jalgaon", 21.0077, 75.5626, ["APMC Jalgaon", "Jalgaon(Masawat)"]),
    ("Chalisgaon APMC", "चाळीसगाव", "Jalgaon", 20.4620, 75.0160, ["APMC Chalisgaon"]),
    ("Solapur APMC", "सोलापूर", "Solapur", 17.6599, 75.9064, ["APMC Solapur"]),
    ("Pandharpur APMC", "पंढरपूर", "Solapur", 17.6790, 75.3310, ["APMC Pandharpur"]),
    ("Sangola APMC", "सांगोला", "Solapur", 17.4380, 75.1940, ["APMC Sangola"]),
    ("Chhatrapati Sambhajinagar APMC", "छत्रपती संभाजीनगर (जाधववाडी)", "Chhatrapati Sambhajinagar", 19.8975, 75.3524, ["APMC Chattrapati Sambhajinagar"]),
    ("Yavatmal APMC", "यवतमाळ", "Yavatmal", 20.3888, 78.1204, ["APMC Yavatmal"]),
    ("Wardha APMC", "वर्धा", "Wardha", 20.7453, 78.6022, ["APMC Wardha"]),
    ("Akola APMC", "अकोला", "Akola", 20.7002, 77.0082, ["APMC Akola"]),
    ("Nanded APMC", "नांदेड", "Nanded", 19.1383, 77.3210, ["APMC Nanded"]),
    ("Hingoli APMC", "हिंगोली", "Hingoli", 19.7173, 77.1490, ["APMC Hingoli"]),
    ("Parbhani APMC", "परभणी", "Parbhani", 19.2608, 76.7748, ["APMC Parbhani"]),
    ("Sangli APMC", "सांगली", "Sangli", 16.8524, 74.5815, ["APMC Sangli", "Sangli(Phale, Bhajipala Market)"]),
    ("Tasgaon APMC", "तासगाव", "Sangli", 17.0370, 74.6010, ["APMC Tasgaon"]),
    ("Kolhapur APMC", "कोल्हापूर", "Kolhapur", 16.7050, 74.2433, ["APMC Kolhapur", "Kolhapur(Laxmipuri)"]),
    ("Dhule APMC", "धुळे", "Dhule", 20.9042, 74.7749, ["APMC Dhule"]),
    ("Satara APMC", "सातारा", "Satara", 17.6805, 74.0183, ["APMC Satara"]),
    ("Mumbai (Vashi) APMC", "मुंबई (वाशी)", "Mumbai", 19.0771, 72.9986, ["APMC Mumbai", "Mumbai-Onion & Potato Market"]),
    ("Majalgaon APMC", "माजलगाव", "Beed", 19.1500, 76.2167, ["APMC Majalgaon"]),
]

WAREHOUSES = [
    ("Niphad WDRA Warehouse", "निफाड वखार (WDRA)", "Nashik", True, 1800),
    ("Lasalgaon Cold & Dry Storage", "लासलगाव साठवण केंद्र", "Nashik", True, 2200),
    ("Latur Central Warehousing", "लातूर केंद्रीय वखार", "Latur", True, 1500),
    ("Ahilyanagar MSWC Godown", "अहिल्यानगर वखार महामंडळ", "Ahmednagar", True, 1600),
    ("Pune Private Storage", "पुणे खाजगी गोदाम", "Pune", False, 2500),
]

LOGISTICS = [
    ("Niphad Tempo Seva", "transport", 20.0800, 74.1100, 5000, "9822044401"),
    ("Lasalgaon Truck Union", "transport", 20.1500, 74.2300, 10000, "9822044402"),
    ("Nashik Kisan Cold Chain", "storage", 20.0000, 73.8000, 200000, "9822044403"),
    ("Latur Grain Movers", "transport", 18.4000, 76.5600, 9000, "9822044404"),
]


def _point(lat: float, lng: float) -> WKTElement:
    return WKTElement(f"POINT({lng} {lat})", srid=4326)


def load_prices(csv_path: Path, commodity_ids: dict[str, int], market_ids: dict[str, int]) -> tuple[list[dict], int, date]:
    """Aggregate the Agmarknet export to one row per (date, mandi, crop)."""
    cmap = {agm: commodity_ids[name] for name, _, _, agms in COMMODITIES for agm in agms}
    mmap = {agm: market_ids[name] for name, *_, agms in MARKETS for agm in agms}
    acc: dict[tuple, dict] = {}
    last_day = date.min
    opener = gzip.open if str(csv_path).endswith(".gz") else open
    with opener(csv_path, "rt", newline="", encoding="utf-8") as f:
        for r in csv.DictReader(f):
            cid, mid = cmap.get(r["Commodity"]), mmap.get(r["Mandi"])
            if cid is None or mid is None:
                continue
            try:
                d = date.fromisoformat(r["Arrival_Date"])
                modal = float(r["Modal_Price"])
                lo = float(r["Min_Price"] or modal)
                hi = float(r["Max_Price"] or modal)
            except (ValueError, KeyError):
                continue
            if modal <= 0:
                continue
            arr = float(r["Arrivals"] or 0)
            arr_qtl = arr * 10 if "tonne" in (r.get("UnitOfArrivals") or "").lower() else arr
            k = (d, mid, cid)
            a = acc.setdefault(k, {"modal": [], "min": [], "max": [], "arr": 0.0})
            a["modal"].append(modal); a["min"].append(lo); a["max"].append(hi); a["arr"] += arr_qtl
            last_day = max(last_day, d)

    target_last = date.today() - timedelta(days=1)
    offset = (target_last - last_day).days if last_day != date.min else 0
    rows = []
    for (d, mid, cid), a in acc.items():
        modal = sum(a["modal"]) / len(a["modal"])
        shifted = d + timedelta(days=offset)
        rows.append({
            "market_id": mid, "commodity_id": cid,
            "date": datetime(shifted.year, shifted.month, shifted.day, tzinfo=timezone.utc),
            "min_price_paise": int(round(min(a["min"]) * 100)),
            "max_price_paise": int(round(max(a["max"]) * 100)),
            # Agmarknet quotes whole rupees; averaging several rows for one
            # day must not invent paise (₹4,600.33 → ₹4,600).
            "modal_price_paise": int(round(modal)) * 100,
            "arrivals_qtl": int(round(a["arr"])),
            "observation_type": "ARCHIVE",
        })
    return rows, offset, last_day


async def reset_schema() -> None:
    async with engine.begin() as conn:
        await conn.execute(text("CREATE EXTENSION IF NOT EXISTS postgis"))
        await conn.execute(text("DROP TABLE IF EXISTS alembic_version"))
        await conn.run_sync(Base.metadata.drop_all)
        await conn.run_sync(Base.metadata.create_all)
        await conn.execute(text("CREATE TABLE IF NOT EXISTS alembic_version (version_num VARCHAR(32) PRIMARY KEY)"))
        await conn.execute(text("DELETE FROM alembic_version"))
        await conn.execute(text(f"INSERT INTO alembic_version VALUES ('{ALEMBIC_HEAD}')"))


async def seed(csv_path: Path) -> None:
    now = datetime.now(timezone.utc)
    async with async_session() as db:
        # ── reference ──────────────────────────────────────────────────────
        districts = {n: District(name=n, name_mr=mr) for n, mr in DISTRICTS}
        db.add_all(districts.values())
        commodities = {n: Commodity(name=n, name_mr=mr, storable_days=sd) for n, mr, sd, _ in COMMODITIES}
        db.add_all(commodities.values())
        await db.flush()
        markets = {}
        for name, mr, dist, lat, lng, _ in MARKETS:
            markets[name] = MandiLocation(name=name, name_mr=mr, district_id=districts[dist].id,
                                          lat=lat, lng=lng, geom=_point(lat, lng))
        db.add_all(markets.values())
        for name, mr, dist, wdra, rent in WAREHOUSES:
            db.add(Warehouse(name=name, name_mr=mr, district_id=districts[dist].id,
                             wdra_registered=wdra, rent_paise_per_qtl_month=rent, source="demo"))
        for name, kind, lat, lng, cap, phone in LOGISTICS:
            db.add(LogisticsProvider(name=name, type=kind, lat=lat, lng=lng, geom=_point(lat, lng),
                                     capacity_kg=cap, contact=phone, source="demo"))
        await db.flush()

        # ── prices ─────────────────────────────────────────────────────────
        rows, offset, last_day = load_prices(csv_path, {n: c.id for n, c in commodities.items()},
                                             {n: m.id for n, m in markets.items()})
        for i in range(0, len(rows), 5000):
            await db.execute(PriceObservation.__table__.insert(), rows[i:i + 5000])
        print(f"prices: {len(rows):,} daily rows; CSV ended {last_day}, shifted +{offset} days (source=ARCHIVE)")

        def latest_modal(commodity: str, market: str) -> int:
            cid, mid = commodities[commodity].id, markets[market].id
            best = max((r for r in rows if r["commodity_id"] == cid and r["market_id"] == mid),
                       key=lambda r: r["date"], default=None)
            # Asking prices and bids are quoted in whole ₹5 steps, never paise.
            return (round(best["modal_price_paise"] / 500) * 500) if best else 200000

        # ── people ─────────────────────────────────────────────────────────
        fpo = FPO(name="Niphad Kanda Utpadak FPO", region="Nashik")
        db.add(fpo)
        await db.flush()

        def user(name, phone, role, dist, village, lat, lng, locale="mr", verified=False):
            return User(name=name, phone=phone, role=role, locale=locale, district_id=districts[dist].id,
                        village=village, lat=lat, lng=lng, geom=_point(lat, lng), verified=verified)

        farmer = user("रामभाऊ पाटील", "9822011111", "FARMER", "Nashik", "Niphad", 20.0800, 74.1100)
        sunita = user("सुनीता पवार", "9822033331", "FARMER", "Nashik", "Vinchur", 20.1100, 74.2300)
        ganesh = user("गणेश शिंदे", "9822033332", "FARMER", "Nashik", "Pimpalgaon", 20.1700, 73.9900)
        buyer1 = user("सुरेश मेहता", "9822022222", "BUYER", "Nashik", None, 20.1438, 74.2386, verified=True)
        buyer2 = user("Agro Fresh Exports", "9822022223", "BUYER", "Pune", None, 18.4967, 73.8647, locale="en", verified=True)
        admin = user("FPO Admin Niphad", "9822033333", "FPO_ADMIN", "Nashik", "Niphad", 20.0800, 74.1100)
        db.add_all([farmer, sunita, ganesh, buyer1, buyer2, admin])
        await db.flush()
        for f in (farmer, sunita, ganesh):
            db.add(Farmer(user_id=f.id, fpo_id=fpo.id))
        db.add(Farmer(user_id=admin.id, fpo_id=fpo.id))
        db.add(Buyer(user_id=buyer1.id, company_name="Mehta Onion Traders", verified_status=True,
                     tier="T2_VERIFIED", gst_last4="4821", deals_completed=38,
                     on_time_payment_bps=9600, renegotiation_bps=300))
        db.add(Buyer(user_id=buyer2.id, company_name="Agro Fresh Exports Pvt Ltd", verified_status=True,
                     tier="T2_VERIFIED", gst_last4="1907", deals_completed=112,
                     on_time_payment_bps=9850, renegotiation_bps=120))
        await db.flush()

        # ── lots ───────────────────────────────────────────────────────────
        onion_las = latest_modal("Onion", "Lasalgaon APMC")
        good_assay = {"size_uniform": 3, "colour_uniform": 2, "sprouting": 3,
                      "damage_pct": 6, "moisture_feel": 3, "foreign_matter": 3}

        def lot(owner, commodity, market, kg, price, grade=None, assay=None, status="active", days_ago=1):
            return Lot(farmer_id=owner.id, fpo_id=fpo.id, commodity_id=commodities[commodity].id,
                       market_id=markets[market].id, quantity_qtl=kg // 100, expected_price_paise=price,
                       grade=grade, self_assay_answers=assay, lat=owner.lat, lng=owner.lng,
                       geom=_point(owner.lat, owner.lng), status=status,
                       created_at=now - timedelta(days=days_ago))

        l_onion = lot(farmer, "Onion", "Lasalgaon APMC", 4000, onion_las, "A", good_assay, days_ago=2)
        l_soy = lot(farmer, "Soyabean", "Latur APMC", 1500, None, days_ago=1)
        l_transit = lot(farmer, "Onion", "Pimpalgaon Baswant APMC", 2500,
                        latest_modal("Onion", "Pimpalgaon Baswant APMC"), "B", good_assay, "locked", 6)
        l_sold = lot(farmer, "Tomato", "Pimpalgaon Baswant APMC", 1200,
                     latest_modal("Tomato", "Pimpalgaon Baswant APMC"), "A", good_assay, "sold", 12)
        others = [lot(sunita, "Onion", "Lasalgaon APMC", 3000, onion_las - 3000, "B", days_ago=3),
                  lot(ganesh, "Onion", "Pimpalgaon Baswant APMC", 5000, onion_las + 2000, "A", good_assay, days_ago=1)]
        db.add_all([l_onion, l_soy, l_transit, l_sold, *others])
        await db.flush()

        # ── buyer demand ───────────────────────────────────────────────────
        d1 = BuyerDemand(buyer_id=buyer1.id, commodity_id=commodities["Onion"].id,
                         market_id=markets["Lasalgaon APMC"].id, quantity_qtl=100,
                         expected_price_paise=onion_las, desired_grade="B", status="active",
                         lat=buyer1.lat, lng=buyer1.lng, geom=_point(buyer1.lat, buyer1.lng), source="demo")
        d2 = BuyerDemand(buyer_id=buyer2.id, commodity_id=commodities["Soyabean"].id,
                         market_id=markets["Latur APMC"].id, quantity_qtl=50,
                         expected_price_paise=latest_modal("Soyabean", "Latur APMC"), desired_grade="B",
                         status="active", lat=buyer2.lat, lng=buyer2.lng, geom=_point(buyer2.lat, buyer2.lng), source="demo")
        db.add_all([d1, d2])
        await db.flush()

        # ── offers + escrow ────────────────────────────────────────────────
        def offer(b, l, kg, price, status="OPEN", demand=None, rnd=1, hours_ago=5, note=None):
            o = Offer(demand_id=demand.id if demand else None, buyer_id=b.id, farmer_id=l.farmer_id,
                      price_paise_per_qtl=price, qty_kg=kg, round=rnd, initiator="BUYER", status=status,
                      note=note, expires_at=now + timedelta(days=2), created_at=now - timedelta(hours=hours_ago))
            db.add(o)
            return o

        o1 = offer(buyer1, l_onion, 4000, onion_las - 5000, demand=d1, hours_ago=6,
                   note="माल आजच उचलू शकतो")
        o2 = offer(buyer2, l_onion, 4000, onion_las - 1500, hours_ago=2,
                   note="Export quality — need grade A")
        o3 = offer(buyer1, l_transit, 2500, l_transit.expected_price_paise, "ACCEPTED", hours_ago=24 * 5)
        o4 = offer(buyer2, l_sold, 1200, l_sold.expected_price_paise, "ACCEPTED", hours_ago=24 * 11)
        await db.flush()
        for o, l in ((o1, l_onion), (o2, l_onion), (o3, l_transit), (o4, l_sold)):
            db.add(OfferLot(offer_id=o.id, lot_id=l.id, quantity_allocated_kg=o.qty_kg))

        def tx(o, chain, days_ago):
            t = Transaction(offer_id=o.id, buyer_id=o.buyer_id, farmer_id=o.farmer_id,
                            amount_paise=o.price_paise_per_qtl * (o.qty_kg // 100), status=chain[-1],
                            created_at=now - timedelta(days=days_ago))
            db.add(t)
            return t, chain

        t3, c3 = tx(o3, ["CREATED", "DEPOSIT_HELD", "IN_TRANSIT"], 5)
        t4, c4 = tx(o4, ["CREATED", "DEPOSIT_HELD", "IN_TRANSIT", "INSPECTED", "FUNDS_RELEASED"], 11)
        await db.flush()
        for t, chain, actors in ((t3, c3, [buyer1, buyer1, farmer]),
                                 (t4, c4, [buyer2, buyer2, farmer, buyer2, buyer2])):
            prev = None
            for i, (st, actor) in enumerate(zip(chain, actors)):
                db.add(EscrowEvent(transaction_id=t.id, status_from=prev, status_to=st, actor_id=actor.id,
                                   note=None, created_at=t.created_at + timedelta(hours=6 * i)))
                prev = st

        await db.commit()

    id_resolver.reload()
    print("demo farmer : 9822011111  (रामभाऊ पाटील, Niphad, Nashik)")
    print("demo buyers : 9822022222  (Mehta Onion Traders), 9822022223 (Agro Fresh Exports)")
    print("FPO admin   : 9822033333")


async def main() -> None:
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("--csv", type=Path, default=Path(os.getenv("AGMARKNET_CSV", DEFAULT_CSV)))
    ap.add_argument("--no-reset", action="store_true", help="don't drop and recreate tables")
    args = ap.parse_args()
    if not args.csv.exists():
        sys.exit(f"price CSV not found: {args.csv}")
    if not args.no_reset:
        await reset_schema()
        print("schema: rebuilt from models, stamped at alembic head", ALEMBIC_HEAD)
    await seed(args.csv)
    await engine.dispose()


if __name__ == "__main__":
    asyncio.run(main())
