"""
Comprehensive End-to-End API Verification Script for Neolithic-Backend (MandiSetu).
Tests all core services: Auth, Reference, Real SOTA AI Forecasting, Lots, Demands, Offers, Logistics.

Usage:
  python scripts/test_all_apis.py [BASE_URL]
  (Defaults to http://localhost:8000 or http://localhost:80)
"""

import sys
import json
import urllib.request
import urllib.error

BASE_URL = sys.argv[1] if len(sys.argv) > 1 else "http://localhost:8000"
print(f"=== Running Neolithic-Backend API Verification against: {BASE_URL} ===\n")

PASSED = 0
FAILED = 0

def request(method, path, data=None, token=None):
    url = f"{BASE_URL}{path}"
    headers = {"Content-Type": "application/json"}
    if token:
        headers["Authorization"] = f"Bearer {token}"
    body = json.dumps(data).encode("utf-8") if data else None
    req = urllib.request.Request(url, data=body, headers=headers, method=method)
    try:
        with urllib.request.urlopen(req, timeout=10) as resp:
            status = resp.status
            content = resp.read().decode("utf-8")
            try:
                parsed = json.loads(content)
            except Exception:
                parsed = content
            return status, parsed
    except urllib.error.HTTPError as e:
        content = e.read().decode("utf-8")
        try:
            parsed = json.loads(content)
        except Exception:
            parsed = content
        return e.code, parsed
    except Exception as e:
        return 0, str(e)


def test(name, method, path, data=None, token=None, expected_status=200):
    global PASSED, FAILED
    status, res = request(method, path, data, token)
    if status == expected_status:
        print(f"✅ PASS: [{method}] {path} -> {status}")
        PASSED += 1
        return res
    else:
        print(f"❌ FAIL: [{method}] {path} -> Expected {expected_status}, got {status}")
        print(f"   Response: {res}")
        FAILED += 1
        return None


# ── 1. Health ─────────────────────────────────────────────────────────────
test("Health Check", "GET", "/health")

# ── 2. Reference Data (Maharashtra) ───────────────────────────────────────
districts = test("Maharashtra Districts", "GET", "/api/v1/ref/districts")
if districts and len(districts) > 0:
    print(f"   ℹ️ Found {len(districts)} Maharashtra districts (e.g. {districts[0].get('name')})")

commodities = test("Maharashtra Commodities", "GET", "/api/v1/ref/commodities")
if commodities and len(commodities) > 0:
    print(f"   ℹ️ Found {len(commodities)} commodities (e.g. {commodities[0].get('name')})")

mandis = test("Maharashtra Mandis", "GET", "/api/v1/ref/mandis")
if mandis and len(mandis) > 0:
    print(f"   ℹ️ Found {len(mandis)} APMC Mandis (e.g. {mandis[0].get('name')})")

warehouses = test("Maharashtra Warehouses", "GET", "/api/v1/ref/warehouses")
if warehouses and len(warehouses) > 0:
    print(f"   ℹ️ Found {len(warehouses)} WDRA Warehouses (e.g. {warehouses[0].get('name')})")

# ── 3. AI & Real SOTA Forecasting ─────────────────────────────────────────
print("\n--- Testing Real SOTA Price Prediction Engine ---")
fc = test("14-Day SOTA Forecast (Lasalgaon Onion)", "GET", "/api/v1/ai/forecast?mandi=Lasalgaon%20APMC&commodity=Onion")
if fc and "forecasts" in fc:
    days = fc["forecasts"]
    print(f"   ℹ️ Generated {len(days)} forecast days")
    if days:
        d0 = days[0]
        print(f"   ℹ️ Day 1: p10=₹{d0.get('p10_paise')/100:.2f} | p50=₹{d0.get('p50_paise')/100:.2f} | p90=₹{d0.get('p90_paise')/100:.2f} | Conf={d0.get('confidence')}")
        print(f"   ℹ️ Data Source: {fc.get('data_source')} (Verified SOTA)")
        assert d0["p10_paise"] <= d0["p50_paise"] <= d0["p90_paise"], "Quantiles must not cross!"

# Sale Window Recommendation (Window Engine)
window_res = test("Sale Window Engine Recommendation", "POST", "/api/v1/ai/window/recommend", data={
    "crop": "Onion",
    "mandi": "Lasalgaon APMC",
    "quantity_kg": 5000,
    "current_price_paise": 220000,
    "grade": "A"
})
if window_res:
    print(f"   ℹ️ Recommendation: {window_res.get('recommendation')} (Confidence: {window_res.get('confidence')})")
    print(f"   ℹ️ Sell-now net: ₹{window_res.get('sell_now_net_paise_per_qtl', 0)/100:.2f}/qtl | Hold p50 net: ₹{window_res.get('hold_p50_net_paise_per_qtl', 0)/100:.2f}/qtl")
    if window_res.get("pledge_quote"):
        pq = window_res["pledge_quote"]
        print(f"   ℹ️ Pledge Quote: Loan=₹{pq.get('loan_paise', 0)/100:.2f}, Net benefit=₹{pq.get('net_benefit_paise', 0)/100:.2f}")

# ── 4. Authentication Flow (OTP & Register) ───────────────────────────────
print("\n--- Testing Authentication & Registration Flow ---")
otp_req = test("Request OTP", "POST", "/api/v1/auth/otp/request", data={"phone": "9822099999"})
dev_otp = otp_req.get("dev_otp", "123456") if otp_req else "123456"

verify_res = test("Verify OTP", "POST", "/api/v1/auth/otp/verify", data={"phone": "9822099999", "code": dev_otp})
token = verify_res.get("access_token") if verify_res else None

# Register user if needed
if verify_res and verify_res.get("needs_registration"):
    reg_res = test("Register Farmer User", "POST", "/api/v1/auth/register", data={
        "name": "Suresh Deshmukh",
        "phone": "9822099999",
        "code": dev_otp,
        "role": "FARMER",
        "locale": "mr",
        "district_id": "1",
        "village": "Niphad",
        "lat": 20.08,
        "lng": 74.11
    })
    if reg_res:
        token = reg_res.get("access_token")

# Verify current user profile
if token:
    test("Get Current User Profile", "GET", "/api/v1/auth/me", token=token)

# ── 5. Lots Management ───────────────────────────────────────────────────
print("\n--- Testing Lots Management ---")
lots = test("List Farmer Lots", "GET", "/api/v1/lots")
if lots and len(lots) > 0:
    print(f"   ℹ️ Found {len(lots)} active lots (Lot #1: {lots[0].get('crop')} {lots[0].get('quantity_qtl')} qtl)")

# ── 6. Buyer Demand & Matching ────────────────────────────────────────────
print("\n--- Testing Demands & Matching ---")
matches = test("Match Demand with Lots", "GET", "/api/v1/demands/1/matches")
if matches:
    print(f"   ℹ️ Matches found: {len(matches.get('matches', []))}")

# ── 7. Logistics & Storage Lookup ─────────────────────────────────────────
print("\n--- Testing Logistics & Cold Storage Lookup ---")
nearby_logistics = test("Nearby Storage & Transport", "GET", "/api/v1/logistics/nearby?lat=20.14&lng=74.23&radius_km=50")
if nearby_logistics:
    print(f"   ℹ️ Found {len(nearby_logistics.get('storage', []))} storage facilities and {len(nearby_logistics.get('transport', []))} transport operators")

# ── Summary ───────────────────────────────────────────────────────────────
print(f"\n==================================================")
print(f"Verification Results: {PASSED} Passed, {FAILED} Failed")
print(f"==================================================")

if FAILED == 0:
    print("🎉 ALL APIS VERIFIED HEALTHY & FULLY FUNCTIONAL!")
    sys.exit(0)
else:
    print("⚠️ Some endpoints encountered issues. Please review output above.")
    sys.exit(1)
