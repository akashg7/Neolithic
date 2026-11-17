from sqlalchemy import Column, Integer, String, DateTime, ForeignKey, func
from sqlalchemy.orm import relationship
from app.database import Base


class Transaction(Base):
    __tablename__ = "transactions"

    id = Column(Integer, primary_key=True, index=True)
    offer_id = Column(Integer, ForeignKey("offers.id"), nullable=False, unique=True)
    buyer_id = Column(Integer, ForeignKey("users.id"), nullable=True, index=True)
    farmer_id = Column(Integer, ForeignKey("users.id"), nullable=True, index=True)
    amount_paise = Column(Integer, nullable=False)
    razorpay_order_id = Column(String(100), nullable=True)
    status = Column(String(50), default="CREATED")
    created_at = Column(DateTime(timezone=True), server_default=func.now())

    events = relationship("EscrowEvent", back_populates="transaction", order_by="EscrowEvent.created_at", cascade="all, delete-orphan")
    offer = relationship("Offer")
    disputes = relationship("Dispute", back_populates="transaction", cascade="all, delete-orphan")

    @property
    def total_amount_paise(self) -> int:
        return self.amount_paise

    @total_amount_paise.setter
    def total_amount_paise(self, val: int):
        self.amount_paise = val


class EscrowEvent(Base):
    __tablename__ = "escrow_events"

    id = Column(Integer, primary_key=True, index=True)
    transaction_id = Column(Integer, ForeignKey("transactions.id"), nullable=False, index=True)
    status_from = Column(String(50), nullable=True)
    status_to = Column(String(50), nullable=False)
    actor_id = Column(Integer, ForeignKey("users.id"), nullable=False)
    note = Column(String, nullable=True)
    created_at = Column(DateTime(timezone=True), server_default=func.now())

    transaction = relationship("Transaction", back_populates="events")

    @property
    def from_state(self) -> str:
        return self.status_from

    @from_state.setter
    def from_state(self, val: str):
        self.status_from = val

    @property
    def to_state(self) -> str:
        return self.status_to

    @to_state.setter
    def to_state(self, val: str):
        self.status_to = val

    @property
    def triggered_by_user_id(self) -> int:
        return self.actor_id

    @triggered_by_user_id.setter
    def triggered_by_user_id(self, val: int):
        self.actor_id = val
