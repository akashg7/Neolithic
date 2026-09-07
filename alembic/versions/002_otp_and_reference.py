"""add otp_codes and ensure reference tables exist

Revision ID: 002_otp_and_reference
Revises: 001_ml_pledge
Create Date: 2026-09-07 01:30:00.000000
"""
from typing import Sequence, Union
from alembic import op
import sqlalchemy as sa

revision: str = "002_otp_and_reference"
down_revision: Union[str, None] = "001_ml_pledge"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def table_exists(name: str) -> bool:
    bind = op.get_bind()
    insp = sa.inspect(bind)
    return insp.has_table(name)


def upgrade() -> None:
    # ── districts ────────────────────────────────────────────────────────
    if not table_exists("districts"):
        op.create_table(
            "districts",
            sa.Column("id", sa.Integer(), primary_key=True, autoincrement=True),
            sa.Column("name", sa.String(length=200), nullable=False),
            sa.Column("name_mr", sa.String(length=200), nullable=False),
        )
        op.create_index(op.f("ix_districts_id"), "districts", ["id"], unique=False)

    # ── commodities ──────────────────────────────────────────────────────
    if not table_exists("commodities"):
        op.create_table(
            "commodities",
            sa.Column("id", sa.Integer(), primary_key=True, autoincrement=True),
            sa.Column("name", sa.String(length=200), nullable=False),
            sa.Column("name_mr", sa.String(length=200), nullable=False),
            sa.Column("storable_days", sa.Integer(), nullable=False),
        )
        op.create_index(op.f("ix_commodities_id"), "commodities", ["id"], unique=False)

    # ── warehouses ───────────────────────────────────────────────────────
    if not table_exists("warehouses"):
        op.create_table(
            "warehouses",
            sa.Column("id", sa.Integer(), primary_key=True, autoincrement=True),
            sa.Column("name", sa.String(length=200), nullable=False),
            sa.Column("name_mr", sa.String(length=200), nullable=False),
            sa.Column("district_id", sa.Integer(), nullable=False),
            sa.Column("wdra_registered", sa.Boolean(), server_default="false"),
            sa.Column("rent_paise_per_qtl_month", sa.Integer(), nullable=False),
            sa.Column("source", sa.String(length=100), nullable=False),
        )
        op.create_index(op.f("ix_warehouses_id"), "warehouses", ["id"], unique=False)
        op.create_index(op.f("ix_warehouses_district_id"), "warehouses", ["district_id"], unique=False)

    # ── logistics_cost_routes ────────────────────────────────────────────
    if not table_exists("logistics_cost_routes"):
        op.create_table(
            "logistics_cost_routes",
            sa.Column("id", sa.Integer(), primary_key=True, autoincrement=True),
            sa.Column("from_district_id", sa.Integer(), nullable=False),
            sa.Column("to_market_id", sa.Integer(), nullable=False),
            sa.Column("transport_paise_per_qtl", sa.Integer(), nullable=False),
            sa.Column("commission_bps", sa.Integer(), nullable=False),
            sa.Column("loading_paise_per_qtl", sa.Integer(), nullable=False),
            sa.Column("source", sa.String(length=100), nullable=False),
        )
        op.create_index(op.f("ix_logistics_cost_routes_id"), "logistics_cost_routes", ["id"], unique=False)
        op.create_index(op.f("ix_logistics_cost_routes_from_district_id"), "logistics_cost_routes", ["from_district_id"], unique=False)
        op.create_index(op.f("ix_logistics_cost_routes_to_market_id"), "logistics_cost_routes", ["to_market_id"], unique=False)

    # ── otp_codes ────────────────────────────────────────────────────────
    if not table_exists("otp_codes"):
        op.create_table(
            "otp_codes",
            sa.Column("id", sa.Integer(), primary_key=True, autoincrement=True),
            sa.Column("phone", sa.String(length=20), nullable=False),
            sa.Column("code_hash", sa.String(length=200), nullable=False),
            sa.Column("attempts", sa.Integer(), server_default="0", nullable=True),
            sa.Column("expires_at", sa.DateTime(timezone=True), nullable=False),
            sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=True),
        )
        op.create_index(op.f("ix_otp_codes_id"), "otp_codes", ["id"], unique=False)
        op.create_index(op.f("ix_otp_codes_phone"), "otp_codes", ["phone"], unique=False)


def downgrade() -> None:
    if table_exists("otp_codes"):
        op.drop_table("otp_codes")
