import logging
import runpy
from pathlib import Path

from flask import Flask
import pytest
from sqlalchemy import text
from sqlalchemy.exc import OperationalError

from app import create_app
from app.extensions import db
from config import ProductionConfig, TestingConfig


PROJECT_ROOT = Path(__file__).resolve().parents[1]


class RuntimeProductionConfig(ProductionConfig):
    SECRET_KEY = "runtime-test-only-secret"
    SQLALCHEMY_DATABASE_URI = "sqlite:///:memory:"
    MFA_ENCRYPTION_KEY = TestingConfig.MFA_ENCRYPTION_KEY
    RATELIMIT_ENABLED = False
    RATELIMIT_STORAGE_URI = "redis://rate-limit.example.invalid:6379/0"


def test_gunicorn_configuration_is_conservative_and_local() -> None:
    config = runpy.run_path(str(PROJECT_ROOT / "gunicorn.conf.py"))

    assert config["bind"] == "127.0.0.1:8000"
    assert 1 <= config["workers"] <= 2
    assert config["worker_class"] == "sync"
    assert config["timeout"] > 0
    assert config["graceful_timeout"] > 0
    assert config["keepalive"] > 0
    assert config["accesslog"] == "-"
    assert config["errorlog"] == "-"
    assert config["capture_output"] is True
    assert "%(q)s" not in config["access_log_format"]
    assert "%(r)s" not in config["access_log_format"]


@pytest.mark.parametrize(
    ("configured_level", "expected_level"),
    [
        ("DEBUG", logging.DEBUG),
        ("INFO", logging.INFO),
        ("WARNING", logging.WARNING),
        ("ERROR", logging.ERROR),
        ("CRITICAL", logging.CRITICAL),
    ],
)
def test_valid_production_log_level_does_not_enable_debug(
    configured_level: str,
    expected_level: int,
) -> None:
    class ErrorLogProductionConfig(RuntimeProductionConfig):
        LOG_LEVEL = configured_level

    app = create_app(ErrorLogProductionConfig)

    assert app.logger.level == expected_level
    assert app.debug is False


def test_invalid_log_level_fails_clearly() -> None:
    class InvalidLogProductionConfig(RuntimeProductionConfig):
        LOG_LEVEL = "verbose"

    try:
        create_app(InvalidLogProductionConfig)
    except RuntimeError as error:
        assert "LOG_LEVEL" in str(error)
        assert "verbose" not in str(error)
    else:
        raise AssertionError("Invalid LOG_LEVEL was accepted.")


def test_repeated_app_creation_does_not_duplicate_log_handlers() -> None:
    first_app = create_app("testing")
    handler_count = len(first_app.logger.handlers)

    second_app = create_app("testing")

    assert len(second_app.logger.handlers) == handler_count


def test_sqlite_file_connections_enable_safety_pragmas(tmp_path: Path) -> None:
    class FileDatabaseTestingConfig(TestingConfig):
        pass

    database_path = tmp_path / "runtime.db"
    FileDatabaseTestingConfig.SQLALCHEMY_DATABASE_URI = (
        f"sqlite:///{database_path}"
    )
    app = create_app(FileDatabaseTestingConfig)

    with app.app_context():
        with db.engine.connect() as connection:
            foreign_keys = connection.scalar(text("PRAGMA foreign_keys"))
            busy_timeout = connection.scalar(text("PRAGMA busy_timeout"))
            journal_mode = connection.scalar(text("PRAGMA journal_mode"))
        db.engine.dispose()

    assert foreign_keys == 1
    assert busy_timeout == 30_000
    assert journal_mode == "wal"


def test_health_returns_503_without_database_details(
    app: Flask,
    monkeypatch,
) -> None:
    def fail_query(*_args, **_kwargs):
        raise OperationalError(
            "SELECT 1",
            {},
            Exception("database-url-and-path-must-not-leak"),
        )

    monkeypatch.setattr(db.session, "execute", fail_query)

    response = app.test_client().get("/health")

    assert response.status_code == 503
    assert response.get_json() == {"status": "unavailable"}
    assert b"database-url-and-path-must-not-leak" not in response.data
