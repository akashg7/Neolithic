from pydantic import BaseModel
from typing import List, Literal, Optional

class MatchLotItem(BaseModel):
    lot_id: str
    qty_allocated_kg: int

class MatchRow(BaseModel):
    kind: Literal['SINGLE', 'COMBINATION']
    lots: List[MatchLotItem]
    total_qty_kg: int
    fill_bps: int
    avg_score: int
    grade: Literal['A', 'B', 'C']
    distance_km: float
    score: float
    why_mr: str
    why_en: str

class MatchesRes(BaseModel):
    matches: List[MatchRow]
