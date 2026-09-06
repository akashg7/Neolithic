"""add model_runs, pledge_quotes tables

Note: ``warehouses`` already exists via the reference.Warehouse model /
Base.metadata.create_all (scripts/reset_db.py) — not recreated here.

Revision ID: 001_ml_pledge
Revises: 2c47b09fff3c
Create Date: 2025-01-01 00:00:00.000000
"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects import postgresql

revision: str = "001_ml_pledge"
down_revision: Union[str, None] = "2c47b09fff3c"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    # ── model_runs ─────────────────────────────────────────────────────
    op.create_table(
        "model_runs",
        sa.Column("id", sa.Integer(), primary_key=True, autoincrement=True),
        sa.Column("commodity", sa.String(100), nullable=False, index=True),
        sa.Column("pooled_mandis", postgresql.JSONB(), nullable=False),
        sa.Column("training_rows", sa.Integer(), nullable=False),
        sa.Column("feature_count", sa.Integer(), nullable=False),
        sa.Column("mase_pooled", sa.Float(), nullable=False),
        sa.Column("mase_per_mandi", postgresql.JSONB(), nullable=False),
        sa.Column("coverage_bps_pooled", sa.Integer(), nullable=False),
        sa.Column("coverage_bps_per_mandi", postgresql.JSONB(), nullable=False),
        sa.Column("horizon_days", sa.Integer(), nullable=False),
        sa.Column("quantile_alphas", postgresql.JSONB(), nullable=False),
        sa.Column("data_source", sa.String(20), nullable=False),
        sa.Column("known_limitations", postgresql.JSONB(), nullable=True),
        sa.Column("artifact_path", sa.String(500), nullable=True),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.func.now()),
    )

    # ── pledge_quotes ──────────────────────────────────────────────────
    op.create_table(
        "pledge_quotes",
        sa.Column("id", sa.Integer(), primary_key=True, autoincrement=True),
        sa.Column("lot_id", sa.Integer(), sa.ForeignKey("lots.id"), nullable=True, index=True),
        sa.Column("assessed_value_paise", sa.Integer(), nullable=False),
        sa.Column("loan_paise", sa.Integer(), nullable=False),
        sa.Column("interest_paise", sa.Integer(), nullable=False),
        sa.Column("net_benefit_paise", sa.Integer(), nullable=False),
        sa.Column("hold_days", sa.Integer(), nullable=False),
        sa.Column("ltv_bps", sa.Integer(), nullable=False),
        sa.Column("rate_bps_annual", sa.Integer(), nullable=False),
        sa.Column("warehouse_id", sa.Integer(), sa.ForeignKey("warehouses.id"), nullable=True),
        sa.Column("is_wdra_registered", sa.Boolean(), server_default="true"),
        sa.Column("model_run_id", sa.Integer(), sa.ForeignKey("model_runs.id"), nullable=True),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.func.now()),
    )


def downgrade() -> None:
    op.drop_table("pledge_quotes")
    op.drop_table("model_runs")
