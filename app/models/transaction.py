from sqlalchemy import Column, Integer, String, DateTime, ForeignKey, JSON, func
from app.database import Base


class Transaction(Base):
    __tablename__ = "transactions"

    id = Column(Integer, primary_key=True, index=True)
    offer_id = Column(Integer, ForeignKey("offers.id"), nullable=False, unique=True)
    amount_paise = Column(Integer, nullable=False)
    razorpay_order_id = Column(String(100), nullable=True)
    payment_status = Column(String(30), default="pending")
    # Statuses: pending, created, paid, failed, refunded
    created_at = Column(DateTime(timezone=True), server_default=func.now())


class TransactionEvent(Base):
    __tablename__ = "transaction_events"

    id = Column(Integer, primary_key=True, index=True)
    transaction_id = Column(Integer, ForeignKey("transactions.id"), nullable=False, index=True)
    event_type = Column(String(50), nullable=False)
    # Types: order_created, payment_authorized, payment_captured, payment_failed, refund_initiated
    payload = Column(JSON, nullable=True)
    created_at = Column(DateTime(timezone=True), server_default=func.now())
