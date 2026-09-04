"""create rooms

Revision ID: a6f2c9d8e417
Revises: d4e8a1c2f903
Create Date: 2026-09-04

"""
from alembic import op
import sqlalchemy as sa


revision = "a6f2c9d8e417"
down_revision = "d4e8a1c2f903"
branch_labels = None
depends_on = None


def upgrade():
    op.create_table(
        "rooms",
        sa.Column("id", sa.Integer(), nullable=False),
        sa.Column("datacenter_id", sa.Integer(), nullable=False),
        sa.Column("name", sa.String(length=120), nullable=False),
        sa.Column("code", sa.String(length=64), nullable=False),
        sa.Column("description", sa.String(length=1000), nullable=True),
        sa.Column(
            "status",
            sa.String(length=20),
            server_default="active",
            nullable=False,
        ),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("updated_at", sa.DateTime(timezone=True), nullable=False),
        sa.ForeignKeyConstraint(
            ["datacenter_id"], ["datacenters.id"], ondelete="RESTRICT"
        ),
        sa.PrimaryKeyConstraint("id"),
        sa.UniqueConstraint(
            "datacenter_id", "code", name="uq_rooms_datacenter_code"
        ),
    )


def downgrade():
    op.drop_table("rooms")
