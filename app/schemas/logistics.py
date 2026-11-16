from pydantic import BaseModel, Field
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


class TransportEstimateReq(BaseModel):
    origin_lat: float = Field(..., description="Pickup latitude")
    origin_lng: float = Field(..., description="Pickup longitude")
    dest_lat: float = Field(..., description="Delivery latitude")
    dest_lng: float = Field(..., description="Delivery longitude")
    qty_qtl: int = Field(..., gt=0, description="Quantity in quintals")
    commodity_name: Optional[str] = Field("Onion", description="Crop commodity name")


class TransportEstimateOut(BaseModel):
    distance_km: float
    qty_qtl: int
    base_rate_per_km_paise: int
    estimated_freight_paise: int
    estimated_transit_hours: float
    route_summary: str

