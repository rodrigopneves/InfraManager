"""replace is_admin with role

Revision ID: 1cb1df284d69
Revises: 45741f4c9e40
Create Date: 2026-09-03 09:18:10.489977

"""
from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision = "1cb1df284d69"
down_revision = "45741f4c9e40"
branch_labels = None
depends_on = None


def upgrade():
    with op.batch_alter_table("users", schema=None) as batch_op:
        batch_op.add_column(
            sa.Column(
                "role",
                sa.String(length=20),
                server_default="viewer",
                nullable=False,
            )
        )

    op.execute(sa.text("UPDATE users SET role = 'admin' WHERE is_admin = 1"))

    with op.batch_alter_table("users", schema=None) as batch_op:
        batch_op.drop_column("is_admin")


def downgrade():
    with op.batch_alter_table("users", schema=None) as batch_op:
        batch_op.add_column(
            sa.Column(
                "is_admin",
                sa.Boolean(),
                server_default=sa.text("0"),
                nullable=False,
            )
        )

    op.execute(sa.text("UPDATE users SET is_admin = 1 WHERE role = 'admin'"))

    with op.batch_alter_table("users", schema=None) as batch_op:
        batch_op.drop_column("role")
