from pathlib import Path

from flask import Flask
from sqlalchemy import inspect

from app import create_app
from app.extensions import db
from config import TestingConfig


def test_audit_migration_creates_expected_table_and_indexes(
    tmp_path: Path,
) -> None:
    database_path = tmp_path / "audit-migration.db"

    class MigrationTestingConfig(TestingConfig):
        SQLALCHEMY_DATABASE_URI = f"sqlite:///{database_path}"

    app: Flask = create_app(MigrationTestingConfig)
    runner = app.test_cli_runner()
    previous_revision = runner.invoke(args=["db", "upgrade", "8f2c9a4d1e7b"])
    assert previous_revision.exit_code == 0, previous_revision.output

    migration_result = runner.invoke(args=["db", "upgrade", "b7d3a1f6c942"])
    assert migration_result.exit_code == 0, migration_result.output

    with app.app_context():
        inspector = inspect(db.engine)
        columns = {
            column["name"] for column in inspector.get_columns("audit_logs")
        }
        indexes = {
            index["name"] for index in inspector.get_indexes("audit_logs")
        }
        foreign_keys = {
            tuple(foreign_key["constrained_columns"])
            for foreign_key in inspector.get_foreign_keys("audit_logs")
        }

    assert columns == {
        "id",
        "event_type",
        "actor_user_id",
        "target_user_id",
        "ip_address",
        "user_agent",
        "details",
        "created_at",
    }
    assert indexes == {
        "ix_audit_logs_actor_user_id",
        "ix_audit_logs_created_at",
        "ix_audit_logs_event_type",
        "ix_audit_logs_target_user_id",
    }
    assert foreign_keys == {("actor_user_id",), ("target_user_id",)}
