"""AgentTurnLog ORM model (`agent_turns` table)."""
from __future__ import annotations

from sqlalchemy import Column, DateTime, ForeignKey, Index, Integer, String, Text, func
from sqlalchemy.dialects.postgresql import JSONB

from app.database import Base


class AgentTurnLog(Base):
    """Stores both original/translated inputs and replies plus tool/RAG metadata."""

    __tablename__ = "agent_turns"
    __table_args__ = (
        Index("ix_agent_turns_session_created", "session_id", "created_at"),
    )

    id = Column(Integer, primary_key=True, index=True)
    turn_id = Column(String(64), unique=True, nullable=False, index=True)
    session_id = Column(String(128), nullable=False, index=True)
    user_id = Column(Integer, ForeignKey("users.id"), nullable=True, index=True)
    locale = Column(String(10), nullable=False, default="mr")
    channel = Column(String(16), nullable=False, default="text")
    screen_context = Column(JSONB, nullable=True)
    original_text = Column(Text, nullable=True)
    english_text = Column(Text, nullable=True)
    transcript = Column(Text, nullable=True)
    english_reply = Column(Text, nullable=True)
    reply_text = Column(Text, nullable=True)
    intent_detected = Column(String(50), nullable=True)
    tools_called = Column(JSONB, nullable=True)
    rag_sources = Column(JSONB, nullable=True)
    latency_ms = Column(Integer, nullable=True)
    error_code = Column(String(64), nullable=True)
    created_at = Column(DateTime(timezone=True), server_default=func.now())
