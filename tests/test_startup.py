import importlib
import sys

import pytest
from flask import Flask

from app import create_app, create_wsgi_app
from config import ProductionConfig
from config import TestingConfig


def test_explicit_development_configuration_remains_available() -> None:
    app = create_app("development")

    assert app.debug is True


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

    app = create_wsgi_app("production")

    assert isinstance(app, Flask)
    assert app.debug is False


def test_production_rejects_all_missing_required_settings(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    monkeypatch.setattr(ProductionConfig, "SECRET_KEY", None)
    monkeypatch.setattr(ProductionConfig, "SQLALCHEMY_DATABASE_URI", None)
    monkeypatch.setattr(ProductionConfig, "MFA_ENCRYPTION_KEY", None)

    with pytest.raises(RuntimeError) as error:
        create_wsgi_app("production")

    message = str(error.value)
    assert "DATABASE_URL" in message
    assert "SECRET_KEY" in message
    assert "MFA_ENCRYPTION_KEY" in message


def test_wsgi_exports_flask_application(monkeypatch: pytest.MonkeyPatch) -> None:
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
    sys.modules.pop("wsgi", None)
    app = importlib.import_module("wsgi").app

    assert isinstance(app, Flask)
    assert app.view_functions["main.health"] is not None
