"""create racks

Revision ID: f3b7c1e9a204
Revises: a6f2c9d8e417
Create Date: 2026-09-04

"""
from alembic import op
import sqlalchemy as sa


revision = "f3b7c1e9a204"
down_revision = "a6f2c9d8e417"
branch_labels = None
depends_on = None


def upgrade():
    op.create_table(
        "racks",
        sa.Column("id", sa.Integer(), nullable=False),
        sa.Column("room_id", sa.Integer(), nullable=False),
        sa.Column("name", sa.String(length=120), nullable=False),
        sa.Column("code", sa.String(length=64), nullable=False),
        sa.Column("capacity_u", sa.Integer(), nullable=False),
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
            "capacity_u >= 1 AND capacity_u <= 100",
            name="ck_racks_capacity_u_range",
        ),
        sa.ForeignKeyConstraint(
            ["room_id"], ["rooms.id"], ondelete="RESTRICT"
        ),
        sa.PrimaryKeyConstraint("id"),
        sa.UniqueConstraint("room_id", "code", name="uq_racks_room_code"),
    )


def downgrade():
    op.drop_table("racks")
