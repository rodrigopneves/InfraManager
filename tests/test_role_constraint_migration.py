from pathlib import Path

import pytest
from flask import Flask
from sqlalchemy import inspect, text
from sqlalchemy.exc import IntegrityError

from app import create_app
from app.extensions import db
from config import TestingConfig


PARENT_REVISION = "c2f4a6b8d105"
ROLE_CHECK_REVISION = "9d6e2f4a1b30"


def test_role_check_upgrade_and_downgrade(tmp_path: Path) -> None:
    database_path = tmp_path / "role-check-migration.db"

    class MigrationTestingConfig(TestingConfig):
        SQLALCHEMY_DATABASE_URI = f"sqlite:///{database_path}"

    app: Flask = create_app(MigrationTestingConfig)
    runner = app.test_cli_runner()
    parent_upgrade = runner.invoke(args=["db", "upgrade", PARENT_REVISION])
    assert parent_upgrade.exit_code == 0, parent_upgrade.output

    with app.app_context():
        for index, role in enumerate(("admin", "operator", "viewer"), start=1):
            db.session.execute(
                text(
                    "INSERT INTO users "
                    "(username, email, password_hash, is_active, role, mfa_enabled, "
                    "created_at, updated_at) VALUES "
                    "(:username, :email, 'hash', 1, :role, 0, "
                    "CURRENT_TIMESTAMP, CURRENT_TIMESTAMP)"
                ),
                {
                    "username": f"role{index}.demo",
                    "email": f"role{index}@example.com",
                    "role": role,
                },
            )
        db.session.commit()

    upgrade = runner.invoke(args=["db", "upgrade", ROLE_CHECK_REVISION])
    assert upgrade.exit_code == 0, upgrade.output
    with app.app_context():
        stored_roles = set(
            db.session.execute(text("SELECT role FROM users")).scalars()
        )
        assert stored_roles == {"admin", "operator", "viewer"}
        checks = {
            constraint["name"]
            for constraint in inspect(db.engine).get_check_constraints("users")
        }
        assert "ck_users_role" in checks
        with pytest.raises(IntegrityError):
            db.session.execute(
                text(
                    "INSERT INTO users "
                    "(username, email, password_hash, is_active, role, mfa_enabled, "
                    "created_at, updated_at) VALUES "
                    "('invalid.role', 'invalid.role@example.com', 'hash', 1, "
                    "'manager', 0, CURRENT_TIMESTAMP, CURRENT_TIMESTAMP)"
                )
            )
            db.session.commit()
        db.session.rollback()

    downgrade = runner.invoke(args=["db", "downgrade", PARENT_REVISION])
    assert downgrade.exit_code == 0, downgrade.output
    with app.app_context():
        checks = {
            constraint["name"]
            for constraint in inspect(db.engine).get_check_constraints("users")
        }
        assert "ck_users_role" not in checks
