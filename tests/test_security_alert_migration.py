from pathlib import Path

from flask import Flask
from sqlalchemy import inspect

from app import create_app
from app.extensions import db
from config import TestingConfig
from tests.helpers import dispose_database


PREVIOUS_REVISION = "a4c8e2d7f105"
SECURITY_ALERT_REVISION = "d9f4b2a7c610"


def test_security_alert_migration_round_trip(tmp_path: Path) -> None:
    database_path = tmp_path / "security-alert-migration.db"

    class MigrationTestingConfig(TestingConfig):
        SQLALCHEMY_DATABASE_URI = f"sqlite:///{database_path}"

    app: Flask = create_app(MigrationTestingConfig)
    runner = app.test_cli_runner()
    assert runner.invoke(args=["db", "upgrade", PREVIOUS_REVISION]).exit_code == 0

    upgrade = runner.invoke(args=["db", "upgrade", SECURITY_ALERT_REVISION])
    assert upgrade.exit_code == 0, upgrade.output
    _assert_security_alert_schema(app)

    downgrade = runner.invoke(args=["db", "downgrade", PREVIOUS_REVISION])
    assert downgrade.exit_code == 0, downgrade.output
    with app.app_context():
        assert "security_alerts" not in inspect(db.engine).get_table_names()

    second_upgrade = runner.invoke(
        args=["db", "upgrade", SECURITY_ALERT_REVISION]
    )
    assert second_upgrade.exit_code == 0, second_upgrade.output
    _assert_security_alert_schema(app)
    dispose_database(app)


def _assert_security_alert_schema(app: Flask) -> None:
    with app.app_context():
        inspector = inspect(db.engine)
        columns = {
            column["name"] for column in inspector.get_columns("security_alerts")
        }
        indexes = {
            index["name"] for index in inspector.get_indexes("security_alerts")
        }
        checks = {
            constraint["name"]
            for constraint in inspector.get_check_constraints("security_alerts")
        }
        foreign_keys = {
            tuple(foreign_key["constrained_columns"])
            for foreign_key in inspector.get_foreign_keys("security_alerts")
        }

    assert columns == {
        "id",
        "event_type",
        "severity",
        "status",
        "user_id",
        "ip_address",
        "user_agent",
        "endpoint",
        "occurrence_count",
        "first_seen_at",
        "last_seen_at",
        "reviewed_at",
        "reviewed_by_user_id",
    }
    assert indexes == {
        "ix_security_alerts_event_type",
        "ix_security_alerts_last_seen_at",
        "ix_security_alerts_severity",
        "ix_security_alerts_status",
        "ix_security_alerts_user_id",
    }
    assert checks == {
        "ck_security_alerts_occurrence_count",
        "ck_security_alerts_severity",
        "ck_security_alerts_status",
    }
    assert foreign_keys == {("user_id",), ("reviewed_by_user_id",)}
