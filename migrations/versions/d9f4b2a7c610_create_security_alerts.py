"""create security alerts

Revision ID: d9f4b2a7c610
Revises: a4c8e2d7f105
Create Date: 2026-09-05 12:00:00.000000

"""
from alembic import op
import sqlalchemy as sa


revision = "d9f4b2a7c610"
down_revision = "a4c8e2d7f105"
branch_labels = None
depends_on = None


def upgrade():
    op.create_table(
        "security_alerts",
        sa.Column("id", sa.Integer(), nullable=False),
        sa.Column("event_type", sa.String(length=50), nullable=False),
        sa.Column("severity", sa.String(length=10), nullable=False),
        sa.Column(
            "status",
            sa.String(length=10),
            server_default="new",
            nullable=False,
        ),
        sa.Column("user_id", sa.Integer(), nullable=True),
        sa.Column("ip_address", sa.String(length=45), nullable=True),
        sa.Column("user_agent", sa.String(length=255), nullable=True),
        sa.Column("endpoint", sa.String(length=120), nullable=True),
        sa.Column(
            "occurrence_count",
            sa.Integer(),
            server_default="1",
            nullable=False,
        ),
        sa.Column("first_seen_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("last_seen_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("reviewed_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("reviewed_by_user_id", sa.Integer(), nullable=True),
        sa.CheckConstraint(
            "occurrence_count >= 1",
            name="ck_security_alerts_occurrence_count",
        ),
        sa.CheckConstraint(
            "severity IN ('WARNING', 'ERROR', 'CRITICAL')",
            name="ck_security_alerts_severity",
        ),
        sa.CheckConstraint(
            "status IN ('new', 'reviewed')",
            name="ck_security_alerts_status",
        ),
        sa.ForeignKeyConstraint(
            ["reviewed_by_user_id"], ["users.id"], ondelete="SET NULL"
        ),
        sa.ForeignKeyConstraint(["user_id"], ["users.id"], ondelete="SET NULL"),
        sa.PrimaryKeyConstraint("id"),
    )
    op.create_index(
        "ix_security_alerts_event_type",
        "security_alerts",
        ["event_type"],
        unique=False,
    )
    op.create_index(
        "ix_security_alerts_last_seen_at",
        "security_alerts",
        ["last_seen_at"],
        unique=False,
    )
    op.create_index(
        "ix_security_alerts_severity",
        "security_alerts",
        ["severity"],
        unique=False,
    )
    op.create_index(
        "ix_security_alerts_status",
        "security_alerts",
        ["status"],
        unique=False,
    )
    op.create_index(
        "ix_security_alerts_user_id",
        "security_alerts",
        ["user_id"],
        unique=False,
    )


def downgrade():
    op.drop_index("ix_security_alerts_user_id", table_name="security_alerts")
    op.drop_index("ix_security_alerts_status", table_name="security_alerts")
    op.drop_index("ix_security_alerts_severity", table_name="security_alerts")
    op.drop_index("ix_security_alerts_last_seen_at", table_name="security_alerts")
    op.drop_index("ix_security_alerts_event_type", table_name="security_alerts")
    op.drop_table("security_alerts")
