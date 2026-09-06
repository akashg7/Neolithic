from sqlalchemy import Column, Integer, String, DateTime, ForeignKey, JSON, func
from app.database import Base


class Transaction(Base):
    __tablename__ = "transactions"

    id = Column(Integer, primary_key=True, index=True)
    offer_id = Column(Integer, ForeignKey("offers.id"), nullable=False, unique=True)
    amount_paise = Column(Integer, nullable=False)
    razorpay_order_id = Column(String(100), nullable=True)
    status = Column(String(50), default="PENDING_BUYER_DEPOSIT")
    created_at = Column(DateTime(timezone=True), server_default=func.now())


class EscrowEvent(Base):
    __tablename__ = "escrow_events"

    id = Column(Integer, primary_key=True, index=True)
    transaction_id = Column(Integer, ForeignKey("transactions.id"), nullable=False, index=True)
    status_from = Column(String(50), nullable=True)
    status_to = Column(String(50), nullable=False)
    actor_id = Column(Integer, ForeignKey("users.id"), nullable=False)
    note = Column(String, nullable=True)
    created_at = Column(DateTime(timezone=True), server_default=func.now())
