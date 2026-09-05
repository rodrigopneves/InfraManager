from pathlib import Path

from flask import Flask
from sqlalchemy import inspect

from app import create_app
from app.extensions import db
from config import TestingConfig
from tests.helpers import dispose_database


ASSET_REVISION = "e1a5b7c9d302"
VIRTUAL_MACHINE_REVISION = "c2f4a6b8d105"


def test_virtual_machine_migration_upgrade_downgrade_and_reupgrade(
    tmp_path: Path,
) -> None:
    database_path = tmp_path / "virtual-machine-migration.db"

    class MigrationTestingConfig(TestingConfig):
        SQLALCHEMY_DATABASE_URI = f"sqlite:///{database_path}"

    app: Flask = create_app(MigrationTestingConfig)
    runner = app.test_cli_runner()
    assert runner.invoke(args=["db", "upgrade", ASSET_REVISION]).exit_code == 0
    upgraded = runner.invoke(args=["db", "upgrade", VIRTUAL_MACHINE_REVISION])
    assert upgraded.exit_code == 0, upgraded.output
    _assert_virtual_machine_schema(app)
    downgraded = runner.invoke(args=["db", "downgrade", ASSET_REVISION])
    assert downgraded.exit_code == 0, downgraded.output
    with app.app_context():
        inspector = inspect(db.engine)
        assert "virtual_machines" not in inspector.get_table_names()
        assert "assets" in inspector.get_table_names()
    reupgraded = runner.invoke(args=["db", "upgrade", VIRTUAL_MACHINE_REVISION])
    assert reupgraded.exit_code == 0, reupgraded.output
    _assert_virtual_machine_schema(app)
    dispose_database(app)


def _assert_virtual_machine_schema(app: Flask) -> None:
    with app.app_context():
        inspector = inspect(db.engine)
        columns = {
            column["name"]: column
            for column in inspector.get_columns("virtual_machines")
        }
        unique_constraints = {
            tuple(item["column_names"])
            for item in inspector.get_unique_constraints("virtual_machines")
        }
        checks = {
            item["name"]
            for item in inspector.get_check_constraints("virtual_machines")
        }
        foreign_keys = inspector.get_foreign_keys("virtual_machines")
    assert set(columns) == {
        "id",
        "host_asset_id",
        "name",
        "hostname",
        "ip_address",
        "operating_system",
        "vcpu",
        "memory_mb",
        "disk_gb",
        "environment",
        "status",
        "description",
        "created_at",
        "updated_at",
    }
    assert columns["host_asset_id"]["nullable"] is False
    assert columns["status"]["default"] is not None
    assert unique_constraints == {("name",)}
    assert checks == {
        "ck_virtual_machines_disk_gb",
        "ck_virtual_machines_environment",
        "ck_virtual_machines_memory_mb",
        "ck_virtual_machines_status",
        "ck_virtual_machines_vcpu",
    }
    assert len(foreign_keys) == 1
    assert foreign_keys[0]["constrained_columns"] == ["host_asset_id"]
    assert foreign_keys[0]["referred_table"] == "assets"
    assert foreign_keys[0]["options"].get("ondelete") == "RESTRICT"
