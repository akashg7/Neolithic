"""Pledge models — pledge quote records (warehouses live in app.models.reference)."""

from sqlalchemy import Column, Integer, String, Boolean, DateTime, ForeignKey, func
from sqlalchemy.dialects.postgresql import JSONB
from app.database import Base


class PledgeQuoteRecord(Base):
    """Persisted pledge quotes for traceability and audit."""
    __tablename__ = "pledge_quotes"

    id = Column(Integer, primary_key=True, index=True)
    lot_id = Column(Integer, ForeignKey("lots.id"), nullable=True, index=True)
    assessed_value_paise = Column(Integer, nullable=False)
    loan_paise = Column(Integer, nullable=False)
    interest_paise = Column(Integer, nullable=False)
    net_benefit_paise = Column(Integer, nullable=False)
    hold_days = Column(Integer, nullable=False)
    ltv_bps = Column(Integer, nullable=False)
    rate_bps_annual = Column(Integer, nullable=False)
    warehouse_id = Column(Integer, ForeignKey("warehouses.id"), nullable=True)
    is_wdra_registered = Column(Boolean, default=True)
    model_run_id = Column(Integer, ForeignKey("model_runs.id"), nullable=True)
    created_at = Column(DateTime(timezone=True), server_default=func.now())
