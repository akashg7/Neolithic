from pydantic import BaseModel
from typing import Optional


class LogisticsProviderOut(BaseModel):
    id: int
    name: str
    type: str
    lat: float
    lng: float
    distance_km: Optional[float] = None
    capacity_kg: Optional[int] = None
    contact: Optional[str] = None
    source: str = "demo"

    class Config:
        from_attributes = True


class LogisticsListResponse(BaseModel):
    providers: list[LogisticsProviderOut]
