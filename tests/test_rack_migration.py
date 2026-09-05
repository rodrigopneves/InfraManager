from pathlib import Path

from flask import Flask
from sqlalchemy import inspect

from app import create_app
from app.extensions import db
from config import TestingConfig
from tests.helpers import dispose_database


ROOM_REVISION = "a6f2c9d8e417"
RACK_REVISION = "f3b7c1e9a204"


def test_rack_migration_upgrade_downgrade_and_reupgrade(tmp_path: Path) -> None:
    database_path = tmp_path / "rack-migration.db"

    class MigrationTestingConfig(TestingConfig):
        SQLALCHEMY_DATABASE_URI = f"sqlite:///{database_path}"

    app: Flask = create_app(MigrationTestingConfig)
    runner = app.test_cli_runner()
    previous = runner.invoke(args=["db", "upgrade", ROOM_REVISION])
    assert previous.exit_code == 0, previous.output
    upgraded = runner.invoke(args=["db", "upgrade", RACK_REVISION])
    assert upgraded.exit_code == 0, upgraded.output
    _assert_rack_schema(app)

    downgraded = runner.invoke(args=["db", "downgrade", ROOM_REVISION])
    assert downgraded.exit_code == 0, downgraded.output
    with app.app_context():
        inspector = inspect(db.engine)
        assert "racks" not in inspector.get_table_names()
        assert "rooms" in inspector.get_table_names()

    reupgraded = runner.invoke(args=["db", "upgrade", RACK_REVISION])
    assert reupgraded.exit_code == 0, reupgraded.output
    _assert_rack_schema(app)
    dispose_database(app)


def _assert_rack_schema(app: Flask) -> None:
    with app.app_context():
        inspector = inspect(db.engine)
        columns = {column["name"] for column in inspector.get_columns("racks")}
        unique_constraints = {
            tuple(constraint["column_names"])
            for constraint in inspector.get_unique_constraints("racks")
        }
        check_constraints = {
            constraint["name"]
            for constraint in inspector.get_check_constraints("racks")
        }
        foreign_keys = inspector.get_foreign_keys("racks")

    assert columns == {
        "id",
        "room_id",
        "name",
        "code",
        "capacity_u",
        "description",
        "status",
        "created_at",
        "updated_at",
    }
    assert unique_constraints == {("room_id", "code")}
    assert "ck_racks_capacity_u_range" in check_constraints
    assert len(foreign_keys) == 1
    assert foreign_keys[0]["constrained_columns"] == ["room_id"]
    assert foreign_keys[0]["referred_table"] == "rooms"
    assert foreign_keys[0]["options"].get("ondelete") == "RESTRICT"
