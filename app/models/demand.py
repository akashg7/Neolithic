from sqlalchemy import Column, Integer, String, Float, ForeignKey
from sqlalchemy.orm import relationship
from geoalchemy2 import Geometry
from app.database import Base


class BuyerDemand(Base):
    __tablename__ = "buyer_demands"

    id = Column(Integer, primary_key=True, index=True)
    buyer_id = Column(Integer, ForeignKey("users.id"), nullable=False, index=True)
    commodity_id = Column(Integer, ForeignKey("commodities.id"), nullable=False, index=True)
    market_id = Column(Integer, ForeignKey("mandi_locations.id"), nullable=True, index=True)
    warehouse_id = Column(Integer, ForeignKey("warehouses.id"), nullable=True, index=True)
    quantity_qtl = Column(Integer, nullable=False)
    expected_price_paise = Column(Integer, nullable=True)
    desired_grade = Column(String(5), nullable=True)
    status = Column(String(30), default="active", index=True)
    lat = Column(Float, nullable=True)
    lng = Column(Float, nullable=True)
    geom = Column(Geometry('POINT', srid=4326), nullable=True, index=True)
    source = Column(String(10), default="real")  # 'real' or 'demo'
