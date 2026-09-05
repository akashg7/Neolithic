from sqlalchemy import Column, Integer, String, Float, ForeignKey, DateTime, func
from geoalchemy2 import Geometry
from app.database import Base


class MandiLocation(Base):
    __tablename__ = "mandi_locations"

    id = Column(Integer, primary_key=True, index=True)
    name = Column(String(200), nullable=False)
    district = Column(String(200), nullable=False)
    lat = Column(Float, nullable=False)
    lng = Column(Float, nullable=False)
    geom = Column(Geometry('POINT', srid=4326), nullable=True, index=True)


class PriceForecast(Base):
    __tablename__ = "price_forecasts"

    id = Column(Integer, primary_key=True, index=True)
    mandi = Column(String(200), nullable=False, index=True)
    commodity = Column(String(100), nullable=False, index=True)
    date = Column(DateTime, nullable=False)
    p10_paise = Column(Integer, nullable=False)
    p50_paise = Column(Integer, nullable=False)
    p90_paise = Column(Integer, nullable=False)
    forecast_confidence = Column(Float, nullable=False)  # 0.0 to 1.0
    generated_at = Column(DateTime(timezone=True), server_default=func.now())
