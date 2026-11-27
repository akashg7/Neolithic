"""PostGIS spatial query helpers with graceful fallback for non-PostgreSQL test sessions."""
from __future__ import annotations

import math
from typing import Any, Optional

from geoalchemy2 import Geography
from geoalchemy2.elements import WKTElement
from sqlalchemy import and_, cast, func


def is_postgres(db: Any) -> bool:
    """Return True when the AsyncSession is bound to a PostgreSQL/PostGIS engine."""
    if db is None:
        return False
    try:
        bind = getattr(db, "bind", None)
        if bind is None and hasattr(db, "get_bind"):
            bind = db.get_bind()
        dialect = getattr(bind, "dialect", None)
        return getattr(dialect, "name", None) == "postgresql"
    except Exception:
        return False


def make_wkt_point(lat: Optional[float], lng: Optional[float]) -> Optional[WKTElement]:
    """Build an SRID 4326 POINT WKTElement for GeoAlchemy2 Geometry columns."""
    if lat is None or lng is None:
        return None
    return WKTElement(f"POINT({float(lng)} {float(lat)})", srid=4326)


def st_point(lat: float, lng: float) -> Any:
    """PostGIS SRID-4326 point SQL expression from (lat, lng)."""
    return func.ST_SetSRID(func.ST_MakePoint(float(lng), float(lat)), 4326)


def bbox_envelope(lat: float, lng: float, radius_km: float) -> Any:
    """Conservative WGS-84 bounding box covering `radius_km` around (lat, lng) for GIST `&&` pruning."""
    lat_f = float(lat)
    lng_f = float(lng)
    r_km = max(0.1, float(radius_km))
    delta_lat = (r_km / 110.574) + 0.05
    cos_lat = max(0.2, abs(math.cos(math.radians(lat_f))))
    delta_lng = (r_km / (111.320 * cos_lat)) + 0.05
    return func.ST_MakeEnvelope(
        lng_f - delta_lng,
        lat_f - delta_lat,
        lng_f + delta_lng,
        lat_f + delta_lat,
        4326,
    )


def within_radius_filter(geom_col: Any, lat: float, lng: float, radius_km: float) -> Any:
    """GIST bounding-box prefilter (`&&`) + exact spheroidal `ST_DWithin` on Geography."""
    ref_pt = st_point(lat, lng)
    return and_(
        geom_col.is_not(None),
        geom_col.op("&&")(bbox_envelope(lat, lng, radius_km)),
        func.ST_DWithin(
            cast(geom_col, Geography),
            cast(ref_pt, Geography),
            float(radius_km) * 1000.0,
        ),
    )


def distance_km_expr(geom_col: Any, lat: float, lng: float) -> Any:
    """Exact WGS-84 spheroidal distance in kilometers via PostGIS `ST_Distance(..., Geography)`."""
    ref_pt = st_point(lat, lng)
    return func.ST_Distance(
        cast(geom_col, Geography),
        cast(ref_pt, Geography),
    ) / 1000.0
