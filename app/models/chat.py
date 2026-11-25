"""Direct buyer-farmer negotiation thread message model."""
from sqlalchemy import Column, DateTime, ForeignKey, Integer, String, Text, func

from app.database import Base


class ThreadMessage(Base):
    __tablename__ = "thread_messages"

    id = Column(Integer, primary_key=True, index=True)
    thread_id = Column(String(100), nullable=False, index=True)
    sender_id = Column(Integer, ForeignKey("users.id"), nullable=False, index=True)
    sender_name = Column(String(120), nullable=False)
    text = Column(Text, nullable=False)
    created_at = Column(DateTime(timezone=True), server_default=func.now())
