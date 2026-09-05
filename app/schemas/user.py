from pydantic import BaseModel
from typing import Optional


class UserOut(BaseModel):
    id: int
    name: str
    phone: str
    role: str
    lat: Optional[float] = None
    lng: Optional[float] = None
    preferred_language: str = "en"
    verified: bool = False

    class Config:
        from_attributes = True
