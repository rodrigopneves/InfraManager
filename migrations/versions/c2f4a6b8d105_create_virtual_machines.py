"""create virtual machines

Revision ID: c2f4a6b8d105
Revises: e1a5b7c9d302
Create Date: 2026-09-04 00:00:00.000000

"""
from alembic import op
import sqlalchemy as sa


revision = "c2f4a6b8d105"
down_revision = "e1a5b7c9d302"
branch_labels = None
depends_on = None


def upgrade():
    op.create_table(
        "virtual_machines",
        sa.Column("id", sa.Integer(), nullable=False),
        sa.Column("host_asset_id", sa.Integer(), nullable=False),
        sa.Column("name", sa.String(length=120), nullable=False),
        sa.Column("hostname", sa.String(length=253), nullable=True),
        sa.Column("ip_address", sa.String(length=45), nullable=True),
        sa.Column("operating_system", sa.String(length=120), nullable=True),
        sa.Column("vcpu", sa.Integer(), nullable=False),
        sa.Column("memory_mb", sa.Integer(), nullable=False),
        sa.Column("disk_gb", sa.Integer(), nullable=False),
        sa.Column("environment", sa.String(length=20), nullable=False),
        sa.Column(
            "status",
            sa.String(length=20),
            server_default="stopped",
            nullable=False,
        ),
        sa.Column("description", sa.String(length=1000), nullable=True),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("updated_at", sa.DateTime(timezone=True), nullable=False),
        sa.CheckConstraint(
            "disk_gb BETWEEN 1 AND 1048576",
            name="ck_virtual_machines_disk_gb",
        ),
        sa.CheckConstraint(
            "environment IN ('production', 'staging', 'development', 'test', 'other')",
            name="ck_virtual_machines_environment",
        ),
        sa.CheckConstraint(
            "memory_mb BETWEEN 128 AND 4194304",
            name="ck_virtual_machines_memory_mb",
        ),
        sa.CheckConstraint(
            "status IN ('running', 'stopped', 'suspended', 'maintenance')",
            name="ck_virtual_machines_status",
        ),
        sa.CheckConstraint(
            "vcpu BETWEEN 1 AND 512",
            name="ck_virtual_machines_vcpu",
        ),
        sa.ForeignKeyConstraint(
            ["host_asset_id"], ["assets.id"], ondelete="RESTRICT"
        ),
        sa.PrimaryKeyConstraint("id"),
        sa.UniqueConstraint("name", name="uq_virtual_machines_name"),
    )


def downgrade():
    op.drop_table("virtual_machines")
