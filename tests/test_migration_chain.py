from pathlib import Path

from flask import Flask
from sqlalchemy import inspect

from app import create_app
from app.extensions import db
from config import TestingConfig


RACK_REVISION = "f3b7c1e9a204"
ROOM_REVISION = "a6f2c9d8e417"


def test_empty_database_upgrade_and_single_downgrade_round_trip(
    tmp_path: Path,
) -> None:
    database_path = tmp_path / "complete-migration-chain.db"

    class MigrationTestingConfig(TestingConfig):
        SQLALCHEMY_DATABASE_URI = f"sqlite:///{database_path}"

    app: Flask = create_app(MigrationTestingConfig)
    runner = app.test_cli_runner()

    upgrade_result = runner.invoke(args=["db", "upgrade"])
    assert upgrade_result.exit_code == 0, upgrade_result.output
    _assert_head_schema(app)

    downgrade_result = runner.invoke(
        args=["db", "downgrade", ROOM_REVISION]
    )
    assert downgrade_result.exit_code == 0, downgrade_result.output
    with app.app_context():
        table_names = inspect(db.engine).get_table_names()
        assert "rooms" in table_names
        assert "racks" not in table_names

    second_upgrade = runner.invoke(args=["db", "upgrade", RACK_REVISION])
    assert second_upgrade.exit_code == 0, second_upgrade.output
    _assert_head_schema(app)


def _assert_head_schema(app: Flask) -> None:
    with app.app_context():
        inspector = inspect(db.engine)
        table_names = set(inspector.get_table_names())
        user_columns = {
            column["name"] for column in inspector.get_columns("users")
        }
        audit_columns = {
            column["name"] for column in inspector.get_columns("audit_logs")
        }

    assert "users" in table_names
    assert "audit_logs" in table_names
    assert "datacenters" in table_names
    assert "rooms" in table_names
    assert "racks" in table_names
    assert "role" in user_columns
    assert "is_admin" not in user_columns
    assert "mfa_enabled" in user_columns
    assert "mfa_secret" in user_columns
    assert {"resource_type", "resource_id", "result"} <= audit_columns
