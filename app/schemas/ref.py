from pydantic import BaseModel, field_validator, Field

class DistrictOut(BaseModel):
    id: str
    name: str
    name_mr: str
    
    @field_validator("id", mode="before")
    def id_to_str(cls, v): return str(v)
    
    class Config:
        from_attributes = True

class CommodityOut(BaseModel):
    id: str
    name: str
    name_mr: str
    
    @field_validator("id", mode="before")
    def id_to_str(cls, v): return str(v)
    
    class Config:
        from_attributes = True

class WarehouseOut(BaseModel):
    id: str
    name: str
    name_mr: str
    district_id: str
    wdra_registered: bool
    
    @field_validator("id", "district_id", mode="before")
    def id_to_str(cls, v): return str(v)
    
    class Config:
        from_attributes = True

class MandiOut(BaseModel):
    id: str
    name: str
    name_mr: str
    district_id: str
    lat: float
    lon: float = Field(validation_alias="lng")
    
    @field_validator("id", "district_id", mode="before")
    def id_to_str(cls, v): return str(v)
    
    class Config:
        from_attributes = True
