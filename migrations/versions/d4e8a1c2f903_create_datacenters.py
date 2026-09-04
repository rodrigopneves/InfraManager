"""create datacenters

Revision ID: d4e8a1c2f903
Revises: b7d3a1f6c942
Create Date: 2026-09-04

"""
from alembic import op
import sqlalchemy as sa


revision = "d4e8a1c2f903"
down_revision = "b7d3a1f6c942"
branch_labels = None
depends_on = None


def upgrade():
    op.create_table(
        "datacenters",
        sa.Column("id", sa.Integer(), nullable=False),
        sa.Column("name", sa.String(length=120), nullable=False),
        sa.Column("code", sa.String(length=64), nullable=False),
        sa.Column("location", sa.String(length=255), nullable=False),
        sa.Column("description", sa.String(length=1000), nullable=True),
        sa.Column(
            "status",
            sa.String(length=20),
            server_default="active",
            nullable=False,
        ),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("updated_at", sa.DateTime(timezone=True), nullable=False),
        sa.PrimaryKeyConstraint("id"),
        sa.UniqueConstraint("code", name="uq_datacenters_code"),
    )

    with op.batch_alter_table("audit_logs", schema=None) as batch_op:
        batch_op.add_column(sa.Column("resource_type", sa.String(50), nullable=True))
        batch_op.add_column(sa.Column("resource_id", sa.Integer(), nullable=True))
        batch_op.add_column(sa.Column("result", sa.String(20), nullable=True))


def downgrade():
    with op.batch_alter_table("audit_logs", schema=None) as batch_op:
        batch_op.drop_column("result")
        batch_op.drop_column("resource_id")
        batch_op.drop_column("resource_type")

    op.drop_table("datacenters")
