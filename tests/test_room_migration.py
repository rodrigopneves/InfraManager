from pathlib import Path

from flask import Flask
from sqlalchemy import inspect

from app import create_app
from app.extensions import db
from config import TestingConfig


DATACENTER_REVISION = "d4e8a1c2f903"
ROOM_REVISION = "a6f2c9d8e417"


def test_room_migration_upgrade_downgrade_and_reupgrade(tmp_path: Path) -> None:
    database_path = tmp_path / "room-migration.db"

    class MigrationTestingConfig(TestingConfig):
        SQLALCHEMY_DATABASE_URI = f"sqlite:///{database_path}"

    app: Flask = create_app(MigrationTestingConfig)
    runner = app.test_cli_runner()
    previous = runner.invoke(args=["db", "upgrade", DATACENTER_REVISION])
    assert previous.exit_code == 0, previous.output

    upgraded = runner.invoke(args=["db", "upgrade", ROOM_REVISION])
    assert upgraded.exit_code == 0, upgraded.output
    _assert_room_schema(app)

    downgraded = runner.invoke(args=["db", "downgrade", DATACENTER_REVISION])
    assert downgraded.exit_code == 0, downgraded.output
    with app.app_context():
        inspector = inspect(db.engine)
        assert "rooms" not in inspector.get_table_names()
        assert "datacenters" in inspector.get_table_names()

    reupgraded = runner.invoke(args=["db", "upgrade", ROOM_REVISION])
    assert reupgraded.exit_code == 0, reupgraded.output
    _assert_room_schema(app)


def _assert_room_schema(app: Flask) -> None:
    with app.app_context():
        inspector = inspect(db.engine)
        columns = {
            column["name"]: column for column in inspector.get_columns("rooms")
        }
        unique_constraints = {
            tuple(constraint["column_names"])
            for constraint in inspector.get_unique_constraints("rooms")
        }
        foreign_keys = inspector.get_foreign_keys("rooms")

    assert set(columns) == {
        "id",
        "datacenter_id",
        "name",
        "code",
        "description",
        "status",
        "created_at",
        "updated_at",
    }
    assert columns["datacenter_id"]["nullable"] is False
    assert unique_constraints == {("datacenter_id", "code")}
    assert len(foreign_keys) == 1
    assert foreign_keys[0]["constrained_columns"] == ["datacenter_id"]
    assert foreign_keys[0]["referred_table"] == "datacenters"
    assert foreign_keys[0]["options"].get("ondelete") == "RESTRICT"
