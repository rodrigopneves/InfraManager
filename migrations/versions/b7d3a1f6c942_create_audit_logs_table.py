"""create audit logs table

Revision ID: b7d3a1f6c942
Revises: 8f2c9a4d1e7b
Create Date: 2026-09-03

"""
from alembic import op
import sqlalchemy as sa


revision = "b7d3a1f6c942"
down_revision = "8f2c9a4d1e7b"
branch_labels = None
depends_on = None


def upgrade():
    op.create_table(
        "audit_logs",
        sa.Column("id", sa.Integer(), nullable=False),
        sa.Column("event_type", sa.String(length=50), nullable=False),
        sa.Column("actor_user_id", sa.Integer(), nullable=True),
        sa.Column("target_user_id", sa.Integer(), nullable=True),
        sa.Column("ip_address", sa.String(length=45), nullable=True),
        sa.Column("user_agent", sa.String(length=255), nullable=True),
        sa.Column("details", sa.JSON(), nullable=False),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False),
        sa.ForeignKeyConstraint(
            ["actor_user_id"], ["users.id"], ondelete="SET NULL"
        ),
        sa.ForeignKeyConstraint(
            ["target_user_id"], ["users.id"], ondelete="SET NULL"
        ),
        sa.PrimaryKeyConstraint("id"),
    )
    op.create_index(
        op.f("ix_audit_logs_actor_user_id"),
        "audit_logs",
        ["actor_user_id"],
        unique=False,
    )
    op.create_index(
        op.f("ix_audit_logs_created_at"),
        "audit_logs",
        ["created_at"],
        unique=False,
    )
    op.create_index(
        op.f("ix_audit_logs_event_type"),
        "audit_logs",
        ["event_type"],
        unique=False,
    )
    op.create_index(
        op.f("ix_audit_logs_target_user_id"),
        "audit_logs",
        ["target_user_id"],
        unique=False,
    )


def downgrade():
    op.drop_index(
        op.f("ix_audit_logs_target_user_id"), table_name="audit_logs"
    )
    op.drop_index(
        op.f("ix_audit_logs_event_type"), table_name="audit_logs"
    )
    op.drop_index(
        op.f("ix_audit_logs_created_at"), table_name="audit_logs"
    )
    op.drop_index(
        op.f("ix_audit_logs_actor_user_id"), table_name="audit_logs"
    )
    op.drop_table("audit_logs")
