"""support encrypted mfa secrets and replay state

Revision ID: a4c8e2d7f105
Revises: 9d6e2f4a1b30
Create Date: 2026-09-04 21:00:00.000000

"""
from alembic import op
import sqlalchemy as sa


revision = "a4c8e2d7f105"
down_revision = "9d6e2f4a1b30"
branch_labels = None
depends_on = None


def upgrade():
    with op.batch_alter_table("users", schema=None) as batch_op:
        batch_op.alter_column(
            "mfa_secret",
            existing_type=sa.String(length=64),
            type_=sa.String(length=255),
            existing_nullable=True,
        )
        batch_op.add_column(
            sa.Column("mfa_last_used_step", sa.BigInteger(), nullable=True)
        )


def downgrade():
    with op.batch_alter_table("users", schema=None) as batch_op:
        batch_op.drop_column("mfa_last_used_step")
        batch_op.alter_column(
            "mfa_secret",
            existing_type=sa.String(length=255),
            type_=sa.String(length=64),
            existing_nullable=True,
        )
