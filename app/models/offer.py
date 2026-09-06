from sqlalchemy import Column, Integer, String, DateTime, ForeignKey, func
from sqlalchemy.orm import relationship
from app.database import Base


class Offer(Base):
    __tablename__ = "offers"

    id = Column(Integer, primary_key=True, index=True)
    demand_id = Column(Integer, ForeignKey("buyer_demands.id"), nullable=True)
    buyer_id = Column(Integer, ForeignKey("users.id"), nullable=False, index=True)
    farmer_id = Column(Integer, ForeignKey("users.id"), nullable=True, index=True)
    pool_id = Column(Integer, nullable=True)
    price_paise_per_qtl = Column(Integer, nullable=False)
    qty_kg = Column(Integer, nullable=False)
    round = Column(Integer, default=1, nullable=False)
    parent_offer_id = Column(Integer, ForeignKey("offers.id"), nullable=True)
    initiator = Column(String(20), nullable=False) # 'BUYER' | 'FARMER'
    status = Column(String(30), default="OPEN") # OPEN|ACCEPTED|REJECTED|COUNTERED|EXPIRED|WITHDRAWN
    note = Column(String, nullable=True)
    expires_at = Column(DateTime(timezone=True), nullable=True)
    created_at = Column(DateTime(timezone=True), server_default=func.now())

    parent_offer = relationship("Offer", remote_side=[id])

    lots = relationship("OfferLot", back_populates="offer")


class OfferLot(Base):
    __tablename__ = "offer_lots"

    offer_id = Column(Integer, ForeignKey("offers.id"), primary_key=True)
    lot_id = Column(Integer, ForeignKey("lots.id"), primary_key=True)
    quantity_allocated_kg = Column(Integer, nullable=False)

    offer = relationship("Offer", back_populates="lots")
    lot = relationship("Lot", back_populates="offer_allocations")
