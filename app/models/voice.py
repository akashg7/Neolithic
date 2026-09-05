from sqlalchemy import Column, Integer, String, DateTime, ForeignKey, func
from app.database import Base


class CallSession(Base):
    __tablename__ = "call_sessions"

    id = Column(Integer, primary_key=True, index=True)
    offer_id = Column(Integer, ForeignKey("offers.id"), nullable=False)
    farmer_user_id = Column(Integer, ForeignKey("users.id"), nullable=False)
    buyer_user_id = Column(Integer, ForeignKey("users.id"), nullable=False)
    provider_session_id = Column(String(200), nullable=True)
    status = Column(String(30), default="initiated")
    started_at = Column(DateTime(timezone=True), server_default=func.now())
    ended_at = Column(DateTime(timezone=True), nullable=True)


class VoiceInteraction(Base):
    __tablename__ = "voice_interactions"

    id = Column(Integer, primary_key=True, index=True)
    user_id = Column(Integer, ForeignKey("users.id"), nullable=False)
    audio_ref = Column(String(500), nullable=True)
    transcript = Column(String, nullable=True)
    language = Column(String(10), nullable=True)
    intent_detected = Column(String(100), nullable=True)
    created_at = Column(DateTime(timezone=True), server_default=func.now())
