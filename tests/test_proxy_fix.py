from collections.abc import Iterator

import pytest
from flask import Flask, jsonify, request
from flask.testing import FlaskClient

from app import create_app
from app.extensions import db, limiter
from app.models import AuditEventType, AuditLog, SecurityAlert, SecurityAlertType
from config import ProductionConfig, TestingConfig


class ProxyProductionConfig(ProductionConfig):
    SECRET_KEY = "proxy-fix-test-only-secret"
    SQLALCHEMY_DATABASE_URI = "sqlite:///:memory:"
    MFA_ENCRYPTION_KEY = TestingConfig.MFA_ENCRYPTION_KEY
    RATELIMIT_ENABLED = False
    RATELIMIT_STORAGE_URI = "redis://rate-limit.example.invalid:6379/0"
    WTF_CSRF_ENABLED = False


def add_request_metadata_route(app: Flask) -> FlaskClient:
    @app.get("/_test/request-metadata")
    def request_metadata():
        return jsonify(
            host=request.host,
            is_secure=request.is_secure,
            limiter_origin=limiter._key_func(),
            remote_addr=request.remote_addr,
        )

    return app.test_client()


def test_development_ignores_forwarded_for() -> None:
    client = add_request_metadata_route(create_app("development"))

    response = client.get(
        "/_test/request-metadata",
        headers={"X-Forwarded-For": "198.51.100.10"},
        environ_overrides={"REMOTE_ADDR": "192.0.2.10"},
    )

    assert response.get_json()["remote_addr"] == "192.0.2.10"


def test_testing_ignores_forwarded_for() -> None:
    client = add_request_metadata_route(create_app("testing"))

    response = client.get(
        "/_test/request-metadata",
        headers={"X-Forwarded-For": "198.51.100.20"},
        environ_overrides={"REMOTE_ADDR": "192.0.2.20"},
    )

    assert response.get_json()["remote_addr"] == "192.0.2.20"


def test_production_trusts_exactly_one_forwarded_client_ip() -> None:
    client = add_request_metadata_route(create_app(ProxyProductionConfig))

    response = client.get(
        "/_test/request-metadata",
        headers={"X-Forwarded-For": "198.51.100.30"},
        environ_overrides={"REMOTE_ADDR": "127.0.0.1"},
    )

    assert response.get_json()["remote_addr"] == "198.51.100.30"


def test_production_forwarded_https_sets_secure_request() -> None:
    client = add_request_metadata_route(create_app(ProxyProductionConfig))

    response = client.get(
        "/_test/request-metadata",
        headers={"X-Forwarded-Proto": "https"},
        environ_overrides={"REMOTE_ADDR": "127.0.0.1"},
    )

    assert response.get_json()["is_secure"] is True


def test_production_multiple_ip_chain_uses_only_nearest_forwarded_value() -> None:
    client = add_request_metadata_route(create_app(ProxyProductionConfig))

    response = client.get(
        "/_test/request-metadata",
        headers={"X-Forwarded-For": "198.51.100.40, 203.0.113.40"},
        environ_overrides={"REMOTE_ADDR": "127.0.0.1"},
    )

    assert response.get_json()["remote_addr"] == "203.0.113.40"


def test_production_does_not_trust_forwarded_host() -> None:
    client = add_request_metadata_route(create_app(ProxyProductionConfig))

    response = client.get(
        "/_test/request-metadata",
        headers={
            "Host": "app.internal",
            "X-Forwarded-Host": "attacker.example",
        },
        environ_overrides={"REMOTE_ADDR": "127.0.0.1"},
    )

    assert response.get_json()["host"] == "app.internal"


@pytest.fixture()
def proxy_production_app() -> Iterator[Flask]:
    application = create_app(ProxyProductionConfig)
    with application.app_context():
        db.create_all()
        yield application
        db.session.remove()
        db.drop_all()
        db.engine.dispose()


def test_security_records_use_proxy_normalized_remote_address(
    proxy_production_app: Flask,
) -> None:
    client = proxy_production_app.test_client()

    response = client.post(
        "/login",
        data={"username": "unknown.demo", "password": "invalid-password"},
        headers={"X-Forwarded-For": "198.51.100.50"},
        environ_overrides={"REMOTE_ADDR": "127.0.0.1"},
    )

    alert = db.session.scalar(
        db.select(SecurityAlert).where(
            SecurityAlert.event_type == SecurityAlertType.LOGIN_FAILURE.value
        )
    )
    audit_log = db.session.scalar(
        db.select(AuditLog).where(
            AuditLog.event_type == AuditEventType.LOGIN_FAILURE.value
        )
    )
    assert response.status_code == 200
    assert alert is not None
    assert audit_log is not None
    assert alert.ip_address == "198.51.100.50"
    assert audit_log.ip_address == "198.51.100.50"


def test_rate_limiter_uses_proxy_normalized_remote_address() -> None:
    client = add_request_metadata_route(create_app(ProxyProductionConfig))

    response = client.get(
        "/_test/request-metadata",
        headers={"X-Forwarded-For": "198.51.100.60"},
        environ_overrides={"REMOTE_ADDR": "127.0.0.1"},
    )
    data = response.get_json()

    assert data["limiter_origin"] == data["remote_addr"] == "198.51.100.60"


def test_forged_forwarded_headers_do_not_change_development_request() -> None:
    client = add_request_metadata_route(create_app("development"))

    response = client.get(
        "/_test/request-metadata",
        headers={
            "Host": "development.local",
            "X-Forwarded-For": "198.51.100.70",
            "X-Forwarded-Host": "attacker.example",
            "X-Forwarded-Proto": "https",
        },
        environ_overrides={"REMOTE_ADDR": "192.0.2.70"},
    )
    data = response.get_json()

    assert data["remote_addr"] == "192.0.2.70"
    assert data["is_secure"] is False
    assert data["host"] == "development.local"
