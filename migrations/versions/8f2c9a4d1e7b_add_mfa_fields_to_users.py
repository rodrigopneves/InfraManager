"""add mfa fields to users

Revision ID: 8f2c9a4d1e7b
Revises: 1cb1df284d69
Create Date: 2026-09-03

"""
from alembic import op
import sqlalchemy as sa


revision = "8f2c9a4d1e7b"
down_revision = "1cb1df284d69"
branch_labels = None
depends_on = None


def upgrade():
    with op.batch_alter_table("users", schema=None) as batch_op:
        batch_op.add_column(
            sa.Column(
                "mfa_enabled",
                sa.Boolean(),
                server_default=sa.text("0"),
                nullable=False,
            )
        )
        batch_op.add_column(
            sa.Column("mfa_secret", sa.String(length=64), nullable=True)
        )


def downgrade():
    with op.batch_alter_table("users", schema=None) as batch_op:
        batch_op.drop_column("mfa_secret")
        batch_op.drop_column("mfa_enabled")
