from pathlib import Path

from flask import Flask
from sqlalchemy import inspect

from app import create_app
from app.extensions import db
from config import TestingConfig


AUDIT_REVISION = "b7d3a1f6c942"
PREVIOUS_REVISION = "8f2c9a4d1e7b"


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
        args=["db", "downgrade", PREVIOUS_REVISION]
    )
    assert downgrade_result.exit_code == 0, downgrade_result.output
    with app.app_context():
        assert "audit_logs" not in inspect(db.engine).get_table_names()

    second_upgrade = runner.invoke(args=["db", "upgrade", AUDIT_REVISION])
    assert second_upgrade.exit_code == 0, second_upgrade.output
    _assert_head_schema(app)


def _assert_head_schema(app: Flask) -> None:
    with app.app_context():
        inspector = inspect(db.engine)
        table_names = set(inspector.get_table_names())
        user_columns = {
            column["name"] for column in inspector.get_columns("users")
        }

    assert "users" in table_names
    assert "audit_logs" in table_names
    assert "role" in user_columns
    assert "is_admin" not in user_columns
    assert "mfa_enabled" in user_columns
    assert "mfa_secret" in user_columns
