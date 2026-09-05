from pathlib import Path

from flask import Flask
from sqlalchemy import inspect

from app import create_app
from app.extensions import db
from config import TestingConfig
from tests.helpers import dispose_database


RACK_REVISION = "f3b7c1e9a204"
ASSET_REVISION = "e1a5b7c9d302"


def test_asset_migration_upgrade_downgrade_and_reupgrade(tmp_path: Path) -> None:
    database_path = tmp_path / "asset-migration.db"

    class MigrationTestingConfig(TestingConfig):
        SQLALCHEMY_DATABASE_URI = f"sqlite:///{database_path}"

    app: Flask = create_app(MigrationTestingConfig)
    runner = app.test_cli_runner()
    assert runner.invoke(args=["db", "upgrade", RACK_REVISION]).exit_code == 0
    upgraded = runner.invoke(args=["db", "upgrade", ASSET_REVISION])
    assert upgraded.exit_code == 0, upgraded.output
    _assert_asset_schema(app)
    downgraded = runner.invoke(args=["db", "downgrade", RACK_REVISION])
    assert downgraded.exit_code == 0, downgraded.output
    with app.app_context():
        inspector = inspect(db.engine)
        assert "assets" not in inspector.get_table_names()
        assert "racks" in inspector.get_table_names()
    reupgraded = runner.invoke(args=["db", "upgrade", ASSET_REVISION])
    assert reupgraded.exit_code == 0, reupgraded.output
    _assert_asset_schema(app)
    dispose_database(app)


def _assert_asset_schema(app: Flask) -> None:
    with app.app_context():
        inspector = inspect(db.engine)
        columns = {column["name"] for column in inspector.get_columns("assets")}
        unique_constraints = {
            tuple(item["column_names"])
            for item in inspector.get_unique_constraints("assets")
        }
        checks = {item["name"] for item in inspector.get_check_constraints("assets")}
        foreign_keys = inspector.get_foreign_keys("assets")
    assert columns == {
        "id", "rack_id", "name", "asset_tag", "serial_number", "manufacturer",
        "model", "asset_type", "rack_unit_start", "rack_units", "description",
        "status", "created_at", "updated_at",
    }
    assert unique_constraints == {("asset_tag",)}
    assert checks == {
        "ck_assets_asset_type", "ck_assets_rack_unit_start_positive",
        "ck_assets_rack_units_positive", "ck_assets_status",
    }
    assert len(foreign_keys) == 1
    assert foreign_keys[0]["constrained_columns"] == ["rack_id"]
    assert foreign_keys[0]["referred_table"] == "racks"
    assert foreign_keys[0]["options"].get("ondelete") == "RESTRICT"
