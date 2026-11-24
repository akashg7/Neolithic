"""Canonical reference-ID resolver.

The app speaks in slugs (`cmd_onion`, `mkt_lasalgaon`, `dist_nashik`), the DB in
integer ids, and farmers in words ("कांदा", "kanda", "Lasalgaon"). Every router,
service and agent tool resolves through here so the three never drift apart.

No migration: the slug is derived from the row's English name (plus a small
override table for the names that don't derive cleanly), and the DB rows are
read once into an in-process catalog — the reference tables are tiny and only
change when someone re-seeds (call `reload()` after seeding).

Resolution order for a reference string:
  1. integer / numeric string           -> that id
  2. exact slug or normalized name      -> that row (English or Marathi name)
  3. alias table (Marathi/Hindi/colloquial)
  4. unique prefix match ("lasalgaon" -> "Lasalgaon APMC")
  5. fuzzy match (difflib ratio >= 0.84), only when it is unambiguous
Anything else raises `ResolveError` carrying the closest candidates so a caller
(or the agent) can ask the farmer which one they meant.
"""

from __future__ import annotations

import asyncio
import difflib
import re
import time
import unicodedata
from dataclasses import dataclass, field
from typing import Literal

from fastapi import HTTPException, status
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

Kind = Literal["commodity", "market", "district"]

_PREFIX: dict[str, str] = {"commodity": "cmd_", "market": "mkt_", "district": "dist_"}

# English DB name -> app slug, where the slug isn't simply the first word.
_SLUG_OVERRIDES: dict[str, dict[str, str]] = {
    "commodity": {
        "Bengal Gram": "cmd_gram",
        "Green Chilli": "cmd_chilli",
        "Red Gram (Tur)": "cmd_tur",
    },
    "market": {
        "Ahilyanagar APMC": "mkt_ahmednagar",
        "Chattrapati Sambhajinagar APMC": "mkt_aurangabad",
        "Chhatrapati Sambhajinagar APMC": "mkt_aurangabad",
        "Pune(Moshi) APMC": "mkt_pune_moshi",
    },
    "district": {
        "Ahmednagar": "dist_ahmednagar",
        "Chhatrapati Sambhajinagar": "dist_aurangabad",
        "Mumbai City": "dist_mumbai_city",
        "Mumbai Suburban": "dist_mumbai_suburban",
        "Mumbai": "dist_mumbai",
    },
}

# Normalized alias -> English DB name. Keys are run through `normalize()` at
# import time, so write them naturally.
_ALIASES: dict[str, dict[str, str]] = {
    "commodity": {
        "kanda": "Onion", "kande": "Onion", "pyaz": "Onion", "pyaaz": "Onion",
        "प्याज": "Onion", "प्याज़": "Onion", "कांदे": "Onion", "कांदा": "Onion",
        "soybean": "Soyabean", "soyabin": "Soyabean", "soyabeen": "Soyabean",
        "सोयाबिन": "Soyabean", "सोयाबीन": "Soyabean",
        "gehu": "Wheat", "gahu": "Wheat", "गेहूं": "Wheat", "गेहूँ": "Wheat", "गहू": "Wheat",
        "tamatar": "Tomato", "टमाटर": "Tomato", "टोमॅटो": "Tomato",
        "kapus": "Cotton", "kapas": "Cotton", "कपास": "Cotton", "कापूस": "Cotton",
        "batata": "Potato", "aloo": "Potato", "aalu": "Potato", "आलू": "Potato", "बटाटा": "Potato",
        "gram": "Bengal Gram", "chana": "Bengal Gram", "harbhara": "Bengal Gram",
        "चना": "Bengal Gram", "हरभरा": "Bengal Gram",
        "chilli": "Green Chilli", "mirchi": "Green Chilli", "मिर्च": "Green Chilli",
        "मिरची": "Green Chilli", "हिरवी मिरची": "Green Chilli",
        "kela": "Banana", "केला": "Banana", "केळी": "Banana",
        "makka": "Maize", "maka": "Maize", "मक्का": "Maize", "मका": "Maize",
        "chawal": "Rice", "dhan": "Rice", "चावल": "Rice", "तांदूळ": "Rice", "भात": "Rice",
        "moongphali": "Groundnut", "shengdana": "Groundnut", "मूंगफली": "Groundnut",
        "भुईमूग": "Groundnut", "शेंगदाणा": "Groundnut",
        "jwari": "Jowar", "jowari": "Jowar", "ज्वार": "Jowar", "ज्वारी": "Jowar",
        "haldi": "Turmeric", "halad": "Turmeric", "हल्दी": "Turmeric", "हळद": "Turmeric",
    },
    "market": {
        "लासलगाव": "Lasalgaon APMC", "लासलगांव": "Lasalgaon APMC",
        "नाशिक": "Nashik APMC", "नासिक": "Nashik APMC",
        "pune": "Pune APMC", "gultekdi": "Pune APMC", "पुणे": "Pune APMC", "गुलटेकडी": "Pune APMC",
        "moshi": "Pune(Moshi) APMC", "मोशी": "Pune(Moshi) APMC",
        "ahmednagar": "Ahilyanagar APMC", "nagar": "Ahilyanagar APMC",
        "अहमदनगर": "Ahilyanagar APMC", "अहिल्यानगर": "Ahilyanagar APMC",
        "aurangabad": "Chattrapati Sambhajinagar APMC",
        "sambhajinagar": "Chattrapati Sambhajinagar APMC",
        "chhatrapati sambhajinagar": "Chattrapati Sambhajinagar APMC",
        "jadhavwadi": "Chattrapati Sambhajinagar APMC",
        "औरंगाबाद": "Chattrapati Sambhajinagar APMC",
        "संभाजीनगर": "Chattrapati Sambhajinagar APMC",
        "kalamna": "Nagpur APMC", "नागपूर": "Nagpur APMC", "नागपुर": "Nagpur APMC",
        "सोलापूर": "Solapur APMC", "सोलापुर": "Solapur APMC",
        "अमरावती": "Amravati APMC", "कोल्हापूर": "Kolhapur APMC", "कोल्हापुर": "Kolhapur APMC",
    },
    "district": {
        "nagar": "Ahmednagar", "ahilyanagar": "Ahmednagar", "अहमदनगर": "Ahmednagar",
        "aurangabad": "Chhatrapati Sambhajinagar", "sambhajinagar": "Chhatrapati Sambhajinagar",
        "औरंगाबाद": "Chhatrapati Sambhajinagar", "संभाजीनगर": "Chhatrapati Sambhajinagar",
        "osmanabad": "Dharashiv", "उस्मानाबाद": "Dharashiv",
        "mumbai": "Mumbai City", "मुंबई": "Mumbai City",
        "नासिक": "Nashik", "पुणे": "Pune", "नागपुर": "Nagpur",
    },
}

# Words that carry no identity ("Lasalgaon APMC" == "Lasalgaon बाजार समिती").
_NOISE = re.compile(
    r"\b(apmc|market|mandi|district|jilha|zilla|yard)\b"
    r"|कृषी उत्पन्न बाजार समिती|कृषी उत्पन्न बाजार|बाजार समिती|मुख्य|मंडी|मार्केट|जिल्हा|जिला|उपबाजार|यार्ड"
)


def normalize(text: str) -> str:
    """NFKC, lowercase, strip slug prefixes, noise words, punctuation, spaces."""
    s = unicodedata.normalize("NFKC", str(text)).lower().strip()
    for p in _PREFIX.values():
        if s.startswith(p):
            s = s[len(p):]
            break
    s = s.replace("_", " ")
    s = _NOISE.sub(" ", s)
    # keep letters/digits of any script (Devanagari marks are category M*)
    s = "".join(ch for ch in s if ch.isalnum() or unicodedata.category(ch).startswith("M"))
    return s


@dataclass(frozen=True)
class RefEntity:
    kind: str
    id: int
    slug: str
    name: str
    name_mr: str
    district_id: int | None = None
    lat: float | None = None
    lng: float | None = None

    def as_dict(self) -> dict:
        d = {"kind": self.kind, "id": self.id, "slug": self.slug,
             "name": self.name, "name_mr": self.name_mr}
        if self.district_id is not None:
            d["district_id"] = self.district_id
        return d


class ResolveError(Exception):
    """Raised when a reference can't be resolved to exactly one row."""

    def __init__(self, kind: str, query: str, candidates: list[RefEntity] | None = None):
        self.kind = kind
        self.query = query
        self.candidates = candidates or []
        what = "ambiguous" if self.candidates else "unknown"
        super().__init__(f"{what} {kind}: {query!r}")

    @property
    def ambiguous(self) -> bool:
        return bool(self.candidates)


def slug_for(kind: str, name: str) -> str:
    override = _SLUG_OVERRIDES.get(kind, {}).get(name)
    if override:
        return override
    first = normalize(name.split("(")[0].split()[0]) if name.strip() else ""
    return f"{_PREFIX[kind]}{first}"


@dataclass
class _Index:
    by_id: dict[int, RefEntity] = field(default_factory=dict)
    exact: dict[str, list[RefEntity]] = field(default_factory=dict)  # normalized key -> rows

    def add(self, e: RefEntity) -> None:
        self.by_id[e.id] = e
        for key in {normalize(e.slug), normalize(e.name), normalize(e.name_mr)}:
            if key:
                self.exact.setdefault(key, [])
                if e not in self.exact[key]:
                    self.exact[key].append(e)


class Catalog:
    """In-memory reference catalog. Build from DB via `load()` or from rows in tests."""

    def __init__(self) -> None:
        self._idx: dict[str, _Index] = {k: _Index() for k in _PREFIX}
        self.loaded = False

    def add(self, kind: str, *, id: int, name: str, name_mr: str = "",
            district_id: int | None = None, lat: float | None = None,
            lng: float | None = None) -> None:
        e = RefEntity(kind=kind, id=int(id), slug=slug_for(kind, name), name=name,
                      name_mr=name_mr or "", district_id=district_id, lat=lat, lng=lng)
        self._idx[kind].add(e)
        self.loaded = True

    def all(self, kind: str) -> list[RefEntity]:
        return list(self._idx[kind].by_id.values())

    def get(self, kind: str, id: int) -> RefEntity | None:
        return self._idx[kind].by_id.get(int(id))

    def resolve(self, kind: str, ref: str | int) -> RefEntity:
        idx = self._idx[kind]
        raw = str(ref).strip()
        if not raw:
            raise ResolveError(kind, raw)

        # 1. integer id
        if raw.isdigit():
            e = idx.by_id.get(int(raw))
            if e is None:
                raise ResolveError(kind, raw)
            return e

        q = normalize(raw)
        if not q:
            raise ResolveError(kind, raw)

        # 2. exact slug / name
        hits = idx.exact.get(q, [])
        if len(hits) == 1:
            return hits[0]
        if len(hits) > 1:
            raise ResolveError(kind, raw, hits)

        # 3. alias
        alias_target = _ALIAS_INDEX[kind].get(q)
        if alias_target:
            hits = idx.exact.get(normalize(alias_target), [])
            if len(hits) == 1:
                return hits[0]

        # 4. unique prefix (either direction, min 4 chars to avoid "na" -> Nashik)
        if len(q) >= 4:
            pref = {e for key, rows in idx.exact.items() if key.startswith(q) for e in rows}
            if len(pref) == 1:
                return pref.pop()
            if len(pref) > 1:
                raise ResolveError(kind, raw, sorted(pref, key=lambda e: e.name))

        # 4b. the query is a longer form of a known name ("लातूरसोयाबीन" → "लातूर"):
        #     take the longest known name the query starts with.
        if len(q) >= 4:
            longer = [(len(key), rows) for key, rows in idx.exact.items()
                      if len(key) >= 4 and q.startswith(key)]
            if longer:
                best_len = max(n for n, _ in longer)
                rows = {e for n, rs in longer if n == best_len for e in rs}
                if len(rows) == 1:
                    return rows.pop()

        # 5. fuzzy
        keys = list(idx.exact.keys()) + list(_ALIAS_INDEX[kind].keys())
        close = difflib.get_close_matches(q, keys, n=3, cutoff=0.84)
        rows: list[RefEntity] = []
        for k in close:
            target_rows = idx.exact.get(k) or idx.exact.get(
                normalize(_ALIAS_INDEX[kind].get(k, "")), [])
            for e in target_rows:
                if e not in rows:
                    rows.append(e)
        if len(rows) == 1:
            return rows[0]
        raise ResolveError(kind, raw, rows)


_ALIAS_INDEX: dict[str, dict[str, str]] = {
    kind: {normalize(k): v for k, v in table.items()} for kind, table in _ALIASES.items()
}

# ── process-wide catalog loaded from the DB ─────────────────────────────────

_catalog = Catalog()
_lock = asyncio.Lock()
_loaded_at = 0.0
CATALOG_TTL_S = 300  # a re-seed (separate process) is picked up within 5 minutes


def _fresh() -> bool:
    return _catalog.loaded and (time.monotonic() - _loaded_at) < CATALOG_TTL_S


async def load_catalog(db: AsyncSession) -> Catalog:
    """Load and return the process catalog (re-read at most every CATALOG_TTL_S)."""
    global _loaded_at
    if _fresh():
        return _catalog
    async with _lock:
        if _fresh():
            return _catalog
        from app.models.reference import Commodity, District
        from app.models.mandi import MandiLocation

        fresh = Catalog()
        for row in (await db.execute(select(Commodity))).scalars():
            fresh.add("commodity", id=row.id, name=row.name, name_mr=row.name_mr)
        for row in (await db.execute(select(District))).scalars():
            fresh.add("district", id=row.id, name=row.name, name_mr=row.name_mr)
        for row in (await db.execute(select(MandiLocation))).scalars():
            fresh.add("market", id=row.id, name=row.name, name_mr=row.name_mr,
                      district_id=row.district_id, lat=row.lat, lng=row.lng)
        if fresh.loaded or not _catalog.loaded:
            _catalog._idx = fresh._idx
            _catalog.loaded = fresh.loaded
        _loaded_at = time.monotonic()
    return _catalog


def slug_of(kind: str, id_value: int | str | None) -> str | None:
    """Sync int-id → app slug for response schemas. Uses the loaded catalog
    (loaded at startup); falls back to the id as a string if it isn't loaded."""
    if id_value is None:
        return None
    s = str(id_value)
    if not s.isdigit():
        return s  # already a slug
    e = _catalog.get(kind, int(s)) if _catalog.loaded else None
    return e.slug if e else s


def reload() -> None:
    """Drop the cached catalog; the next resolve re-reads the DB. Call after seeding."""
    _catalog._idx = {k: _Index() for k in _PREFIX}
    _catalog.loaded = False


async def resolve(db: AsyncSession, kind: Kind, ref: str | int) -> RefEntity:
    return (await load_catalog(db)).resolve(kind, ref)


async def resolve_commodity(db: AsyncSession, ref: str | int) -> int:
    return (await resolve(db, "commodity", ref)).id


async def resolve_market(db: AsyncSession, ref: str | int) -> int:
    return (await resolve(db, "market", ref)).id


async def resolve_district(db: AsyncSession, ref: str | int) -> int:
    return (await resolve(db, "district", ref)).id


async def commodity_slug(db: AsyncSession, id: int) -> str:
    e = (await load_catalog(db)).get("commodity", id)
    if e is None:
        raise ResolveError("commodity", str(id))
    return e.slug


async def resolve_or_404(db: AsyncSession, kind: Kind, ref: str | int, field_name: str) -> RefEntity:
    """Router helper: same as `resolve`, but a miss becomes the standard 404 envelope."""
    try:
        return await resolve(db, kind, ref)
    except ResolveError as exc:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"{field_name}: {exc}",
        ) from exc
