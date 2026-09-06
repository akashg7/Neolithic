from sqlalchemy import Column, Integer, String, Float, ForeignKey, DateTime, func
from sqlalchemy.dialects.postgresql import JSONB
from geoalchemy2 import Geometry
from app.database import Base


class MandiLocation(Base):
    __tablename__ = "mandi_locations"

    id = Column(Integer, primary_key=True, index=True)
    name = Column(String(200), nullable=False)
    name_mr = Column(String(200), nullable=False)
    district_id = Column(Integer, ForeignKey("districts.id"), nullable=False)
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

class PriceObservation(Base):
    __tablename__ = "price_observations"

    id = Column(Integer, primary_key=True, index=True)
    market_id = Column(Integer, ForeignKey("mandi_locations.id"), nullable=True, index=True)
    commodity_id = Column(Integer, ForeignKey("commodities.id"), nullable=False, index=True)
    date = Column(DateTime(timezone=True), nullable=False, index=True)
    min_price_paise = Column(Integer, nullable=True)
    max_price_paise = Column(Integer, nullable=True)
    modal_price_paise = Column(Integer, nullable=False)
    arrivals_qtl = Column(Integer, nullable=True)
    observation_type = Column(String(30), nullable=False) # 'MANDI' or 'APP_DEAL'


class ModelRun(Base):
    """Records each training/backtest run for traceability."""
    __tablename__ = "model_runs"

    id = Column(Integer, primary_key=True, index=True)
    commodity = Column(String(100), nullable=False, index=True)
    pooled_mandis = Column(JSONB, nullable=False)           # list of mandi names
    training_rows = Column(Integer, nullable=False)
    feature_count = Column(Integer, nullable=False)
    mase_pooled = Column(Float, nullable=False)
    mase_per_mandi = Column(JSONB, nullable=False)          # {mandi: float}
    coverage_bps_pooled = Column(Integer, nullable=False)
    coverage_bps_per_mandi = Column(JSONB, nullable=False)  # {mandi: int}
    horizon_days = Column(Integer, nullable=False)
    quantile_alphas = Column(JSONB, nullable=False)         # [0.1, 0.5, 0.9]
    data_source = Column(String(20), nullable=False)        # "real" | "imputed" | "mixed"
    known_limitations = Column(JSONB, nullable=True)
    artifact_path = Column(String(500), nullable=True)      # path to .pkl
    created_at = Column(DateTime(timezone=True), server_default=func.now())
