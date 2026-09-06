import importlib
import sys

import pytest
from flask import Flask

from app import create_app, create_wsgi_app
from config import ProductionConfig
from config import TestingConfig


class CompleteProductionConfig(ProductionConfig):
    SECRET_KEY = "production-startup-test-only-secret"
    SQLALCHEMY_DATABASE_URI = "sqlite:///:memory:"
    MFA_ENCRYPTION_KEY = TestingConfig.MFA_ENCRYPTION_KEY
    RATELIMIT_STORAGE_URI = "redis://rate-limit.example.invalid:6379/0"


def test_explicit_development_configuration_remains_available() -> None:
    app = create_app("development")

    assert app.debug is True
    assert app.config["RATELIMIT_STORAGE_URI"] == "memory://"


def test_testing_configuration_remains_functional() -> None:
    app = create_app("testing")

    assert app.testing is True
    assert app.config["SQLALCHEMY_DATABASE_URI"] == "sqlite:///:memory:"
    assert app.config["RATELIMIT_STORAGE_URI"] == "memory://"


def test_unknown_configuration_is_rejected() -> None:
    with pytest.raises(ValueError, match="Unknown configuration"):
        create_app("missing")


def test_wsgi_requires_explicit_configuration(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    monkeypatch.delenv("FLASK_CONFIG", raising=False)

    with pytest.raises(RuntimeError, match="FLASK_CONFIG"):
        create_wsgi_app()


def test_wsgi_rejects_non_production_configuration() -> None:
    with pytest.raises(RuntimeError, match="production WSGI"):
        create_wsgi_app("development")


def test_wsgi_accepts_complete_production_configuration(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    monkeypatch.setattr(ProductionConfig, "SECRET_KEY", "wsgi-test-only-key")
    monkeypatch.setattr(
        ProductionConfig,
        "MFA_ENCRYPTION_KEY",
        TestingConfig.MFA_ENCRYPTION_KEY,
    )
    monkeypatch.setattr(
        ProductionConfig, "SQLALCHEMY_DATABASE_URI", "sqlite:///:memory:"
    )
    monkeypatch.setattr(
        ProductionConfig,
        "RATELIMIT_STORAGE_URI",
        CompleteProductionConfig.RATELIMIT_STORAGE_URI,
    )

    app = create_wsgi_app("production")

    assert isinstance(app, Flask)
    assert app.debug is False


@pytest.mark.parametrize(
    ("config_attribute", "environment_name"),
    [
        ("SECRET_KEY", "SECRET_KEY"),
        ("SQLALCHEMY_DATABASE_URI", "DATABASE_URL"),
        ("MFA_ENCRYPTION_KEY", "MFA_ENCRYPTION_KEY"),
        ("RATELIMIT_STORAGE_URI", "RATELIMIT_STORAGE_URI"),
    ],
)
def test_production_rejects_missing_required_setting(
    config_attribute: str,
    environment_name: str,
) -> None:
    class MissingSettingProductionConfig(CompleteProductionConfig):
        pass

    setattr(MissingSettingProductionConfig, config_attribute, None)

    with pytest.raises(RuntimeError) as error:
        create_app(MissingSettingProductionConfig)

    assert environment_name in str(error.value)


@pytest.mark.parametrize(
    ("config_attribute", "environment_name"),
    [
        ("SECRET_KEY", "SECRET_KEY"),
        ("SQLALCHEMY_DATABASE_URI", "DATABASE_URL"),
        ("MFA_ENCRYPTION_KEY", "MFA_ENCRYPTION_KEY"),
        ("RATELIMIT_STORAGE_URI", "RATELIMIT_STORAGE_URI"),
    ],
)
def test_production_rejects_empty_required_setting(
    config_attribute: str,
    environment_name: str,
) -> None:
    class EmptySettingProductionConfig(CompleteProductionConfig):
        pass

    setattr(EmptySettingProductionConfig, config_attribute, "   ")

    with pytest.raises(RuntimeError) as error:
        create_app(EmptySettingProductionConfig)

    assert environment_name in str(error.value)


def test_production_rejects_invalid_database_url() -> None:
    class InvalidDatabaseProductionConfig(CompleteProductionConfig):
        SQLALCHEMY_DATABASE_URI = "not-a-database-url"

    with pytest.raises(RuntimeError, match="DATABASE_URL"):
        create_app(InvalidDatabaseProductionConfig)


def test_production_rejects_invalid_rate_limit_storage_uri() -> None:
    class InvalidStorageProductionConfig(CompleteProductionConfig):
        RATELIMIT_STORAGE_URI = "not-a-storage-uri"

    with pytest.raises(RuntimeError, match="RATELIMIT_STORAGE_URI"):
        create_app(InvalidStorageProductionConfig)


def test_production_rejects_memory_rate_limit_storage() -> None:
    class MemoryStorageProductionConfig(CompleteProductionConfig):
        RATELIMIT_STORAGE_URI = "memory://"

    with pytest.raises(RuntimeError, match="RATELIMIT_STORAGE_URI"):
        create_app(MemoryStorageProductionConfig)


def test_production_rejects_async_memory_rate_limit_storage() -> None:
    class AsyncMemoryStorageProductionConfig(CompleteProductionConfig):
        RATELIMIT_STORAGE_URI = "async+memory://"

    with pytest.raises(RuntimeError, match="RATELIMIT_STORAGE_URI"):
        create_app(AsyncMemoryStorageProductionConfig)


def test_production_rejects_unapproved_rate_limit_storage() -> None:
    class UnapprovedStorageProductionConfig(CompleteProductionConfig):
        RATELIMIT_STORAGE_URI = "memcached://rate-limit.example.invalid:11211"

    with pytest.raises(RuntimeError, match="RATELIMIT_STORAGE_URI"):
        create_app(UnapprovedStorageProductionConfig)


@pytest.mark.parametrize("scheme", ["redis", "rediss"])
def test_production_accepts_supported_redis_storage(scheme: str) -> None:
    class RedisProductionConfig(CompleteProductionConfig):
        RATELIMIT_STORAGE_URI = (
            f"{scheme}://rate-limit.example.invalid:6379/0"
        )

    app = create_app(RedisProductionConfig)

    assert app.config["RATELIMIT_STORAGE_URI"].startswith(f"{scheme}://")


def test_redis_storage_preserves_existing_rate_limits() -> None:
    app = create_app(CompleteProductionConfig)

    assert app.config["AUTH_LOGIN_RATE_LIMIT"] == "5 per 15 minutes"
    assert app.config["MFA_SETUP_RATE_LIMIT"] == "5 per 10 minutes"
    assert app.config["MFA_VERIFY_RATE_LIMIT"] == "5 per 5 minutes"
    assert app.config["MFA_DISABLE_RATE_LIMIT"] == "5 per 15 minutes"


def test_production_rejects_debug_enabled() -> None:
    class DebugProductionConfig(CompleteProductionConfig):
        DEBUG = True

    with pytest.raises(RuntimeError, match="DEBUG"):
        create_app(DebugProductionConfig)


def test_production_requires_secure_session_cookie() -> None:
    class InsecureCookieProductionConfig(CompleteProductionConfig):
        SESSION_COOKIE_SECURE = False

    with pytest.raises(RuntimeError, match="SESSION_COOKIE_SECURE"):
        create_app(InsecureCookieProductionConfig)


def test_production_errors_do_not_expose_configuration_values(
    caplog: pytest.LogCaptureFixture,
) -> None:
    class UnsafeProductionConfig(CompleteProductionConfig):
        DEBUG = True
        SECRET_KEY = "secret-value-that-must-not-leak"
        SQLALCHEMY_DATABASE_URI = "invalid-database-value-that-must-not-leak"
        MFA_ENCRYPTION_KEY = "invalid-mfa-value-that-must-not-leak"
        RATELIMIT_STORAGE_URI = (
            "http://redis-user:rate-secret-that-must-not-leak@"
            "rate-limit.example.invalid:6379/0"
        )

    sensitive_values = (
        UnsafeProductionConfig.SECRET_KEY,
        UnsafeProductionConfig.SQLALCHEMY_DATABASE_URI,
        UnsafeProductionConfig.MFA_ENCRYPTION_KEY,
        UnsafeProductionConfig.RATELIMIT_STORAGE_URI,
        "rate-secret-that-must-not-leak",
    )

    with pytest.raises(RuntimeError) as error:
        create_app(UnsafeProductionConfig)

    output = f"{error.value}\n{caplog.text}"
    assert all(value not in output for value in sensitive_values)


def test_wsgi_exports_flask_application(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    monkeypatch.setenv("FLASK_CONFIG", "production")
    monkeypatch.setattr(ProductionConfig, "SECRET_KEY", "wsgi-test-only-key")
    monkeypatch.setattr(
        ProductionConfig,
        "MFA_ENCRYPTION_KEY",
        TestingConfig.MFA_ENCRYPTION_KEY,
    )
    monkeypatch.setattr(
        ProductionConfig, "SQLALCHEMY_DATABASE_URI", "sqlite:///:memory:"
    )
    monkeypatch.setattr(
        ProductionConfig,
        "RATELIMIT_STORAGE_URI",
        CompleteProductionConfig.RATELIMIT_STORAGE_URI,
    )
    sys.modules.pop("wsgi", None)
    app = importlib.import_module("wsgi").app

    assert isinstance(app, Flask)
    assert app.view_functions["main.health"] is not None
