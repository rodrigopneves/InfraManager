from pathlib import Path

from flask import Flask
from sqlalchemy import inspect

from app import create_app
from app.extensions import db
from config import TestingConfig
from tests.helpers import dispose_database


PREVIOUS_REVISION = "b7d3a1f6c942"
DATACENTER_REVISION = "d4e8a1c2f903"


def test_datacenter_migration_upgrade_downgrade_and_reupgrade(
    tmp_path: Path,
) -> None:
    database_path = tmp_path / "datacenter-migration.db"

    class MigrationTestingConfig(TestingConfig):
        SQLALCHEMY_DATABASE_URI = f"sqlite:///{database_path}"

    app: Flask = create_app(MigrationTestingConfig)
    runner = app.test_cli_runner()

    previous_result = runner.invoke(args=["db", "upgrade", PREVIOUS_REVISION])
    assert previous_result.exit_code == 0, previous_result.output

    upgrade_result = runner.invoke(args=["db", "upgrade", DATACENTER_REVISION])
    assert upgrade_result.exit_code == 0, upgrade_result.output
    _assert_datacenter_schema(app)

    downgrade_result = runner.invoke(args=["db", "downgrade", PREVIOUS_REVISION])
    assert downgrade_result.exit_code == 0, downgrade_result.output
    with app.app_context():
        inspector = inspect(db.engine)
        assert "datacenters" not in inspector.get_table_names()
        audit_columns = {
            column["name"] for column in inspector.get_columns("audit_logs")
        }
        assert "resource_type" not in audit_columns
        assert "resource_id" not in audit_columns
        assert "result" not in audit_columns

    reupgrade_result = runner.invoke(args=["db", "upgrade", DATACENTER_REVISION])
    assert reupgrade_result.exit_code == 0, reupgrade_result.output
    _assert_datacenter_schema(app)
    dispose_database(app)


def _assert_datacenter_schema(app: Flask) -> None:
    with app.app_context():
        inspector = inspect(db.engine)
        columns = {
            column["name"] for column in inspector.get_columns("datacenters")
        }
        unique_constraints = {
            tuple(constraint["column_names"])
            for constraint in inspector.get_unique_constraints("datacenters")
        }
        audit_columns = {
            column["name"] for column in inspector.get_columns("audit_logs")
        }

    assert columns == {
        "id",
        "name",
        "code",
        "location",
        "description",
        "status",
        "created_at",
        "updated_at",
    }
    assert unique_constraints == {("code",)}
    assert {"resource_type", "resource_id", "result"} <= audit_columns
