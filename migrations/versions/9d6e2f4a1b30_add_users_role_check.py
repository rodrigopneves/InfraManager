"""add users role check constraint

Revision ID: 9d6e2f4a1b30
Revises: c2f4a6b8d105
Create Date: 2026-09-04 19:00:00.000000

"""
from alembic import op


revision = "9d6e2f4a1b30"
down_revision = "c2f4a6b8d105"
branch_labels = None
depends_on = None


def upgrade():
    with op.batch_alter_table("users", schema=None) as batch_op:
        batch_op.create_check_constraint(
            "ck_users_role",
            "role IN ('admin', 'operator', 'viewer')",
        )


def downgrade():
    with op.batch_alter_table("users", schema=None) as batch_op:
        batch_op.drop_constraint("ck_users_role", type_="check")
