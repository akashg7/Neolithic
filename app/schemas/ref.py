from pydantic import BaseModel

class DistrictOut(BaseModel):
    id: int
    name: str
    name_mr: str
    
    class Config:
        from_attributes = True

class CommodityOut(BaseModel):
    id: int
    name: str
    name_mr: str
    
    class Config:
        from_attributes = True

class WarehouseOut(BaseModel):
    id: int
    name: str
    name_mr: str
    district_id: int
    wdra_registered: bool
    
    class Config:
        from_attributes = True

class MandiOut(BaseModel):
    id: int
    name: str
    name_mr: str
    district_id: int
    lat: float
    lng: float
    
    class Config:
        from_attributes = True
