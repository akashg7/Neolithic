from sqlalchemy import Column, Integer, String, Float, DateTime, ForeignKey, JSON, func
from sqlalchemy.orm import relationship
from geoalchemy2 import Geometry
from app.database import Base


class Lot(Base):
    __tablename__ = "lots"

    id = Column(Integer, primary_key=True, index=True)
    farmer_id = Column(Integer, ForeignKey("users.id"), nullable=False, index=True)
    fpo_id = Column(Integer, ForeignKey("fpos.id"), nullable=True)
    crop = Column(String(100), nullable=False, index=True)
    quantity_kg = Column(Integer, nullable=False)
    grade = Column(String(5), nullable=True)  # A, B, C — set by grading engine
    image_url = Column(String(500), nullable=True)
    self_assay_answers = Column(JSON, nullable=True)
    lat = Column(Float, nullable=True)
    lng = Column(Float, nullable=True)
    geom = Column(Geometry('POINT', srid=4326), nullable=True, index=True)
    price_min_paise_per_qtl = Column(Integer, nullable=True)
    price_mid_paise_per_qtl = Column(Integer, nullable=True)
    price_max_paise_per_qtl = Column(Integer, nullable=True)
    status = Column(String(30), default="active", index=True)
    # Statuses: active, matched, sold, cancelled, aggregated
    created_at = Column(DateTime(timezone=True), server_default=func.now())

    farmer = relationship("User")
    offer_allocations = relationship("OfferLot", back_populates="lot")


class BatchLotMember(Base):
    __tablename__ = "batch_lot_members"

    id = Column(Integer, primary_key=True)
    batch_lot_id = Column(Integer, ForeignKey("lots.id"), nullable=False)
    source_lot_id = Column(Integer, ForeignKey("lots.id"), nullable=False)
    quantity_contributed_kg = Column(Integer, nullable=False)
