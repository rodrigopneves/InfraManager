"""create assets

Revision ID: e1a5b7c9d302
Revises: f3b7c1e9a204
Create Date: 2026-09-04

"""
from alembic import op
import sqlalchemy as sa


revision = "e1a5b7c9d302"
down_revision = "f3b7c1e9a204"
branch_labels = None
depends_on = None


def upgrade():
    op.create_table(
        "assets",
        sa.Column("id", sa.Integer(), nullable=False),
        sa.Column("rack_id", sa.Integer(), nullable=False),
        sa.Column("name", sa.String(length=120), nullable=False),
        sa.Column("asset_tag", sa.String(length=64), nullable=False),
        sa.Column("serial_number", sa.String(length=120), nullable=True),
        sa.Column("manufacturer", sa.String(length=120), nullable=True),
        sa.Column("model", sa.String(length=120), nullable=True),
        sa.Column("asset_type", sa.String(length=30), nullable=False),
        sa.Column("rack_unit_start", sa.Integer(), nullable=False),
        sa.Column("rack_units", sa.Integer(), nullable=False),
        sa.Column("description", sa.String(length=1000), nullable=True),
        sa.Column(
            "status",
            sa.String(length=20),
            server_default="active",
            nullable=False,
        ),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("updated_at", sa.DateTime(timezone=True), nullable=False),
        sa.CheckConstraint(
            "asset_type IN ('server', 'switch', 'router', 'firewall', 'storage', "
            "'appliance', 'access_point', 'notebook', 'desktop', 'other')",
            name="ck_assets_asset_type",
        ),
        sa.CheckConstraint(
            "rack_unit_start >= 1", name="ck_assets_rack_unit_start_positive"
        ),
        sa.CheckConstraint("rack_units >= 1", name="ck_assets_rack_units_positive"),
        sa.CheckConstraint(
            "status IN ('active', 'inactive', 'maintenance')",
            name="ck_assets_status",
        ),
        sa.ForeignKeyConstraint(["rack_id"], ["racks.id"], ondelete="RESTRICT"),
        sa.PrimaryKeyConstraint("id"),
        sa.UniqueConstraint("asset_tag", name="uq_assets_asset_tag"),
    )


def downgrade():
    op.drop_table("assets")
