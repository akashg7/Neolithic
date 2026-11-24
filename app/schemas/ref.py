"""Reference DTOs. Ids go out as the app's canonical slugs (`dist_nashik`,
`cmd_onion`, `mkt_lasalgaon`) — the same strings the app sends back, which every
endpoint accepts (integer ids keep working too)."""

from pydantic import AliasChoices, BaseModel, ConfigDict, Field, field_validator, model_validator
from typing import Any

from app.utils.id_resolver import slug_for, slug_of


def _with_slug(values: Any, kind: str) -> Any:
    """Turn an ORM row into a dict whose `id` is the row's slug."""
    if hasattr(values, "__table__"):
        d = {c.name: getattr(values, c.name) for c in values.__table__.columns}
        d["id"] = slug_for(kind, values.name)
        if "district_id" in d:
            d["district_id"] = slug_of("district", d["district_id"])
        return d
    return values


class DistrictOut(BaseModel):
    model_config = ConfigDict(from_attributes=True)
    id: str
    name: str
    name_mr: str

    @model_validator(mode="before")
    @classmethod
    def slug(cls, v): return _with_slug(v, "district")


class CommodityOut(BaseModel):
    model_config = ConfigDict(from_attributes=True)
    id: str
    name: str
    name_mr: str
    storable_days: int = 0

    @model_validator(mode="before")
    @classmethod
    def slug(cls, v): return _with_slug(v, "commodity")


class WarehouseOut(BaseModel):
    model_config = ConfigDict(from_attributes=True)
    id: str
    name: str
    name_mr: str
    district_id: str
    wdra_registered: bool
    rent_paise_per_qtl_month: int | None = None

    @model_validator(mode="before")
    @classmethod
    def ids(cls, v):
        if hasattr(v, "__table__"):
            d = {c.name: getattr(v, c.name) for c in v.__table__.columns}
            d["id"] = str(v.id)
            d["district_id"] = slug_of("district", v.district_id)
            return d
        return v

    @field_validator("id", "district_id", mode="before")
    @classmethod
    def id_to_str(cls, v): return str(v)


class MandiOut(BaseModel):
    model_config = ConfigDict(from_attributes=True)
    id: str
    name: str
    name_mr: str
    district_id: str
    lat: float
    lon: float = Field(validation_alias=AliasChoices("lng", "lon"))

    @model_validator(mode="before")
    @classmethod
    def slug(cls, v): return _with_slug(v, "market")
