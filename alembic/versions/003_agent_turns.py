"""add agent_turns table for async turn logging

Revision ID: 003_agent_turns
Revises: 002_otp_and_reference
Create Date: 2026-11-25 04:55:00.000000
"""
from typing import Sequence, Union

import sqlalchemy as sa
from alembic import op
from sqlalchemy.dialects import postgresql

revision: str = "003_agent_turns"
down_revision: Union[str, None] = "002_otp_and_reference"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def table_exists(name: str) -> bool:
    bind = op.get_bind()
    insp = sa.inspect(bind)
    return insp.has_table(name)


def upgrade() -> None:
    if not table_exists("agent_turns"):
        op.create_table(
            "agent_turns",
            sa.Column("id", sa.Integer(), primary_key=True, autoincrement=True),
            sa.Column("turn_id", sa.String(length=64), nullable=False, unique=True),
            sa.Column("session_id", sa.String(length=128), nullable=False),
            sa.Column("user_id", sa.Integer(), sa.ForeignKey("users.id"), nullable=True),
            sa.Column("locale", sa.String(length=10), nullable=False, server_default="mr"),
            sa.Column("channel", sa.String(length=16), nullable=False, server_default="text"),
            sa.Column("screen_context", postgresql.JSONB(astext_type=sa.Text()), nullable=True),
            sa.Column("original_text", sa.Text(), nullable=True),
            sa.Column("english_text", sa.Text(), nullable=True),
            sa.Column("transcript", sa.Text(), nullable=True),
            sa.Column("english_reply", sa.Text(), nullable=True),
            sa.Column("reply_text", sa.Text(), nullable=True),
            sa.Column("intent_detected", sa.String(length=50), nullable=True),
            sa.Column("tools_called", postgresql.JSONB(astext_type=sa.Text()), nullable=True),
            sa.Column("rag_sources", postgresql.JSONB(astext_type=sa.Text()), nullable=True),
            sa.Column("latency_ms", sa.Integer(), nullable=True),
            sa.Column("error_code", sa.String(length=64), nullable=True),
            sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=True),
        )
        op.create_index(op.f("ix_agent_turns_id"), "agent_turns", ["id"], unique=False)
        op.create_index(op.f("ix_agent_turns_turn_id"), "agent_turns", ["turn_id"], unique=True)
        op.create_index(op.f("ix_agent_turns_session_id"), "agent_turns", ["session_id"], unique=False)
        op.create_index(op.f("ix_agent_turns_user_id"), "agent_turns", ["user_id"], unique=False)
        op.create_index("ix_agent_turns_session_created", "agent_turns", ["session_id", "created_at"], unique=False)


def downgrade() -> None:
    if table_exists("agent_turns"):
        op.drop_table("agent_turns")
