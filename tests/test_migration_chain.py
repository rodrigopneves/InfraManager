from pathlib import Path
from datetime import datetime, timezone

from flask import Flask
from sqlalchemy import inspect, text

from app import create_app
from app.extensions import db
from config import TestingConfig


ASSET_REVISION = "e1a5b7c9d302"
HEAD_REVISION = "d9f4b2a7c610"


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
        args=["db", "downgrade", ASSET_REVISION]
    )
    assert downgrade_result.exit_code == 0, downgrade_result.output
    with app.app_context():
        table_names = inspect(db.engine).get_table_names()
        assert "assets" in table_names
        assert "virtual_machines" not in table_names

    second_upgrade = runner.invoke(
        args=["db", "upgrade", HEAD_REVISION]
    )
    assert second_upgrade.exit_code == 0, second_upgrade.output
    _assert_head_schema(app)


def _assert_head_schema(app: Flask) -> None:
    with app.app_context():
        inspector = inspect(db.engine)
        table_names = set(inspector.get_table_names())
        user_column_definitions = {
            column["name"]: column for column in inspector.get_columns("users")
        }
        user_columns = set(user_column_definitions)
        audit_columns = {
            column["name"] for column in inspector.get_columns("audit_logs")
        }
        security_alert_columns = {
            column["name"]
            for column in inspector.get_columns("security_alerts")
        }
        user_checks = {
            constraint["name"]
            for constraint in inspector.get_check_constraints("users")
        }

    assert "users" in table_names
    assert "audit_logs" in table_names
    assert "datacenters" in table_names
    assert "rooms" in table_names
    assert "racks" in table_names
    assert "assets" in table_names
    assert "virtual_machines" in table_names
    assert "security_alerts" in table_names
    assert "role" in user_columns
    assert "is_admin" not in user_columns
    assert "mfa_enabled" in user_columns
    assert "mfa_secret" in user_columns
    assert user_column_definitions["mfa_secret"]["type"].length == 255
    assert "mfa_last_used_step" in user_columns
    assert "ck_users_role" in user_checks
    assert {"resource_type", "resource_id", "result"} <= audit_columns
    assert {
        "event_type",
        "severity",
        "status",
        "occurrence_count",
        "first_seen_at",
        "last_seen_at",
    } <= security_alert_columns


def test_mfa_migration_preserves_legacy_secret_for_explicit_encryption(
    tmp_path: Path,
) -> None:
    database_path = tmp_path / "legacy-mfa-migration.db"

    class MigrationTestingConfig(TestingConfig):
        SQLALCHEMY_DATABASE_URI = f"sqlite:///{database_path}"

    app: Flask = create_app(MigrationTestingConfig)
    runner = app.test_cli_runner()
    legacy_secret = "JBSWY3DPEHPK3PXP"
    assert runner.invoke(args=["db", "upgrade", "9d6e2f4a1b30"]).exit_code == 0
    now = datetime.now(timezone.utc).isoformat()
    with app.app_context(), db.engine.begin() as connection:
        connection.execute(
            text(
                """
                INSERT INTO users (
                    username, email, password_hash, is_active, role,
                    mfa_enabled, mfa_secret, created_at, updated_at
                ) VALUES (
                    :username, :email, :password_hash, :is_active, :role,
                    :mfa_enabled, :mfa_secret, :created_at, :updated_at
                )
                """
            ),
            {
                "username": "legacy.migration",
                "email": "legacy.migration@example.com",
                "password_hash": "not-a-real-password-hash",
                "is_active": True,
                "role": "viewer",
                "mfa_enabled": True,
                "mfa_secret": legacy_secret,
                "created_at": now,
                "updated_at": now,
            },
        )

    upgrade_result = runner.invoke(args=["db", "upgrade", HEAD_REVISION])

    assert upgrade_result.exit_code == 0, upgrade_result.output
    with app.app_context(), db.engine.connect() as connection:
        row = connection.execute(
            text(
                "SELECT mfa_secret, mfa_last_used_step "
                "FROM users WHERE username = :username"
            ),
            {"username": "legacy.migration"},
        ).one()
    assert row.mfa_secret == legacy_secret
    assert row.mfa_last_used_step is None
