from sqlalchemy import Column, Integer, String, DateTime, ForeignKey, func
from sqlalchemy.orm import relationship
from app.database import Base


class Offer(Base):
    __tablename__ = "offers"

    id = Column(Integer, primary_key=True, index=True)
    buyer_id = Column(Integer, ForeignKey("users.id"), nullable=False, index=True)
    offered_price_paise_per_qtl = Column(Integer, nullable=False)
    total_quantity_kg = Column(Integer, nullable=False)
    status = Column(String(30), default="pending")
    # Statuses: pending, accepted, rejected, cancelled, paid
    created_at = Column(DateTime(timezone=True), server_default=func.now())

    lots = relationship("OfferLot", back_populates="offer")


class OfferLot(Base):
    __tablename__ = "offer_lots"

    offer_id = Column(Integer, ForeignKey("offers.id"), primary_key=True)
    lot_id = Column(Integer, ForeignKey("lots.id"), primary_key=True)
    quantity_allocated_kg = Column(Integer, nullable=False)

    offer = relationship("Offer", back_populates="lots")
    lot = relationship("Lot", back_populates="offer_allocations")
