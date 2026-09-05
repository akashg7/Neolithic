from pydantic import BaseModel
from typing import Optional


class MandiLocationOut(BaseModel):
    id: int
    name: str
    district: str
    lat: float
    lng: float

    class Config:
        from_attributes = True


class MandiListResponse(BaseModel):
    locations: list[MandiLocationOut]
