from sqlalchemy import Column, Integer, String, Boolean
from app.database import Base

class District(Base):
    __tablename__ = "districts"
    id = Column(Integer, primary_key=True, index=True)
    name = Column(String(200), nullable=False)
    name_mr = Column(String(200), nullable=False)

class Commodity(Base):
    __tablename__ = "commodities"
    id = Column(Integer, primary_key=True, index=True)
    name = Column(String(200), nullable=False)
    name_mr = Column(String(200), nullable=False)
    storable_days = Column(Integer, nullable=False)

class Warehouse(Base):
    __tablename__ = "warehouses"
    id = Column(Integer, primary_key=True, index=True)
    name = Column(String(200), nullable=False)
    name_mr = Column(String(200), nullable=False)
    district_id = Column(Integer, nullable=False, index=True)
    wdra_registered = Column(Boolean, default=False)
    rent_paise_per_qtl_month = Column(Integer, nullable=False)
    source = Column(String(100), nullable=False)

class LogisticsCostRoute(Base):
    __tablename__ = "logistics_cost_routes"
    id = Column(Integer, primary_key=True, index=True)
    from_district_id = Column(Integer, nullable=False, index=True)
    to_market_id = Column(Integer, nullable=False, index=True)
    transport_paise_per_qtl = Column(Integer, nullable=False)
    commission_bps = Column(Integer, nullable=False)
    loading_paise_per_qtl = Column(Integer, nullable=False)
    source = Column(String(100), nullable=False)
