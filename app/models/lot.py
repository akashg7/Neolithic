from sqlalchemy import Column, Integer, String, Float, DateTime, ForeignKey, JSON, func
from sqlalchemy.orm import relationship
from geoalchemy2 import Geometry
from app.database import Base


class Lot(Base):
    __tablename__ = "lots"

    id = Column(Integer, primary_key=True, index=True)
    farmer_id = Column(Integer, ForeignKey("users.id"), nullable=False, index=True)
    fpo_id = Column(Integer, ForeignKey("fpos.id"), nullable=True)
    commodity_id = Column(Integer, ForeignKey("commodities.id"), nullable=False, index=True)
    market_id = Column(Integer, ForeignKey("mandi_locations.id"), nullable=True, index=True)
    warehouse_id = Column(Integer, ForeignKey("warehouses.id"), nullable=True, index=True)
    quantity_qtl = Column(Integer, nullable=False)
    expected_price_paise = Column(Integer, nullable=True)
    grade = Column(String(5), nullable=True)  # A, B, C — set by grading engine
    image_url = Column(String(500), nullable=True)
    self_assay_answers = Column(JSON, nullable=True)
    lat = Column(Float, nullable=True)
    lng = Column(Float, nullable=True)
    geom = Column(Geometry('POINT', srid=4326), nullable=True, index=True)
    status = Column(String(30), default="active", index=True)
    created_at = Column(DateTime(timezone=True), server_default=func.now())

    farmer = relationship("User")
    offer_allocations = relationship("OfferLot", back_populates="lot")


class BatchLotMember(Base):
    __tablename__ = "batch_lot_members"

    id = Column(Integer, primary_key=True)
    batch_lot_id = Column(Integer, ForeignKey("lots.id"), nullable=False)
    source_lot_id = Column(Integer, ForeignKey("lots.id"), nullable=False)
    quantity_contributed_kg = Column(Integer, nullable=False)
