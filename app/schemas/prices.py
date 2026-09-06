from pydantic import BaseModel
from typing import List, Literal, Dict, Optional

DataSource = Literal['AGMARKNET', 'MSAMB', 'ARCHIVE', 'IMPUTED', 'SYNTHETIC']

class PricePoint(BaseModel):
    obs_date: str  # ISO date, YYYY-MM-DD
    min_paise_per_qtl: int
    max_paise_per_qtl: int
    modal_paise_per_qtl: int
    arrivals_qtl: int
    source: DataSource

class PriceSeriesRes(BaseModel):
    points: List[PricePoint]
    source_summary: Dict[DataSource, int]
    latest_obs_date: str

class NearbyMarketRow(BaseModel):
    market_id: str
    name_mr: str
    gross_paise_per_qtl: int
    transport_paise_per_qtl: int
    commission_paise_per_qtl: int
    net_paise_per_qtl: int
    distance_km: int
    source: DataSource

class NearbyRes(BaseModel):
    as_of_date: str
    rows: List[NearbyMarketRow]
    sorted_by: Literal['net_paise_per_qtl']
