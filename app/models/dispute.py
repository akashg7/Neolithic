from sqlalchemy import Column, Integer, String, DateTime, ForeignKey, func
from sqlalchemy.orm import relationship
from app.database import Base


class Dispute(Base):
    __tablename__ = "disputes"

    id = Column(Integer, primary_key=True, index=True)
    transaction_id = Column(Integer, ForeignKey("transactions.id"), nullable=False, index=True)
    raised_by = Column(Integer, ForeignKey("users.id"), nullable=False)
    reason = Column(String(500), nullable=False)
    status = Column(String(30), default="open")
    # Statuses: open, investigating, under_review, resolved, dismissed
    created_at = Column(DateTime(timezone=True), server_default=func.now())

    transaction = relationship("Transaction", back_populates="disputes")

    @property
    def raised_by_id(self) -> int:
        return self.raised_by

    @raised_by_id.setter
    def raised_by_id(self, val: int):
        self.raised_by = val
