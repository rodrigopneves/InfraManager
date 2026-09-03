from pathlib import Path

from flask import Flask
from sqlalchemy import inspect, text

from app import create_app
from app.extensions import db
from config import TestingConfig


def test_migration_converts_legacy_admin_flags(tmp_path: Path) -> None:
    database_path = tmp_path / "rbac-migration.db"

    class MigrationTestingConfig(TestingConfig):
        SQLALCHEMY_DATABASE_URI = f"sqlite:///{database_path}"

    app: Flask = create_app(MigrationTestingConfig)
    runner = app.test_cli_runner()
    old_revision = runner.invoke(
        args=["db", "upgrade", "45741f4c9e40"]
    )
    assert old_revision.exit_code == 0, old_revision.output

    with app.app_context():
        db.session.execute(
            text(
                """
                INSERT INTO users (
                    username, email, password_hash, is_active, is_admin,
                    created_at, updated_at
                ) VALUES
                    ('legacy.admin', 'legacy.admin@example.com', 'hash', 1, 1,
                     CURRENT_TIMESTAMP, CURRENT_TIMESTAMP),
                    ('legacy.viewer', 'legacy.viewer@example.com', 'hash', 1, 0,
                     CURRENT_TIMESTAMP, CURRENT_TIMESTAMP)
                """
            )
        )
        db.session.commit()

    latest_revision = runner.invoke(args=["db", "upgrade"])
    assert latest_revision.exit_code == 0, latest_revision.output

    with app.app_context():
        migrated_roles = dict(
            db.session.execute(text("SELECT username, role FROM users")).all()
        )
        migrated_mfa = dict(
            db.session.execute(
                text("SELECT username, mfa_enabled FROM users")
            ).all()
        )
        columns = {column["name"] for column in inspect(db.engine).get_columns("users")}

    assert migrated_roles == {
        "legacy.admin": "admin",
        "legacy.viewer": "viewer",
    }
    assert "role" in columns
    assert "is_admin" not in columns
    assert migrated_mfa == {"legacy.admin": 0, "legacy.viewer": 0}
    assert "mfa_enabled" in columns
    assert "mfa_secret" in columns
