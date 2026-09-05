import logging
from datetime import datetime, timedelta, timezone

from cryptography.fernet import Fernet
import pyotp
import pytest
from flask import Flask, abort
from flask.testing import FlaskClient
from sqlalchemy.exc import OperationalError

from app.extensions import db
from app.models import (
    AuditEventType,
    AuditLog,
    SecurityAlert,
    SecurityAlertSeverity,
    SecurityAlertStatus,
    SecurityAlertType,
    User,
    UserRole,
)
from app.security_alerts import record_security_event
from tests.helpers import complete_login


def get_alerts(event_type: SecurityAlertType) -> list[SecurityAlert]:
    return db.session.scalars(
        db.select(SecurityAlert)
        .where(SecurityAlert.event_type == event_type.value)
        .order_by(SecurityAlert.id)
    ).all()


def test_invalid_login_emits_warning_and_aggregates_without_secrets(
    app: Flask,
    client: FlaskClient,
    active_user: User,
    caplog: pytest.LogCaptureFixture,
) -> None:
    password = "password-must-stay-private"
    caplog.set_level(logging.WARNING, logger=app.name)

    for _ in range(3):
        response = client.post(
            "/login",
            data={"username": active_user.username, "password": password},
            environ_overrides={"REMOTE_ADDR": "203.0.113.30"},
        )
        assert response.status_code == 200

    alerts = get_alerts(SecurityAlertType.LOGIN_FAILURE)
    audit_count = db.session.scalar(
        db.select(db.func.count())
        .select_from(AuditLog)
        .where(AuditLog.event_type == AuditEventType.LOGIN_FAILURE.value)
    )

    assert len(alerts) == 1
    assert alerts[0].severity == SecurityAlertSeverity.WARNING.value
    assert alerts[0].occurrence_count == 3
    assert alerts[0].ip_address == "203.0.113.30"
    assert audit_count == 3
    assert "security_event=LOGIN_FAILURE" in caplog.text
    assert password not in caplog.text
    assert active_user.password_hash not in caplog.text


def test_inactive_account_attempt_has_distinct_warning(
    app: Flask,
    client: FlaskClient,
    active_user: User,
    caplog: pytest.LogCaptureFixture,
) -> None:
    active_user.is_active = False
    db.session.commit()
    caplog.set_level(logging.WARNING, logger=app.name)

    response = client.post(
        "/login",
        data={
            "username": active_user.username,
            "password": "valid-test-password",
        },
    )

    alert = get_alerts(SecurityAlertType.INACTIVE_ACCOUNT)[0]
    assert response.status_code == 200
    assert alert.user_id == active_user.id
    assert alert.severity == SecurityAlertSeverity.WARNING.value
    assert "security_event=INACTIVE_ACCOUNT" in caplog.text
    assert "valid-test-password" not in caplog.text


def test_enabled_mfa_without_secret_creates_configuration_error(
    app: Flask,
    client: FlaskClient,
    caplog: pytest.LogCaptureFixture,
) -> None:
    user = User(
        username="invalid.mfa",
        email="invalid.mfa@example.com",
        mfa_enabled=True,
    )
    user.set_password("valid-test-password")
    db.session.add(user)
    db.session.commit()
    caplog.set_level(logging.ERROR, logger=app.name)

    response = client.post(
        "/login",
        data={
            "username": user.username,
            "password": "valid-test-password",
        },
    )
    alert = get_alerts(SecurityAlertType.MFA_CONFIGURATION_FAILURE)[0]

    assert response.status_code == 200
    assert alert.user_id == user.id
    assert alert.severity == SecurityAlertSeverity.ERROR.value
    assert "security_event=MFA_CONFIGURATION_FAILURE" in caplog.text


def test_invalid_mfa_emits_warning_without_totp_or_secret(
    app: Flask,
    client: FlaskClient,
    mfa_user: User,
    caplog: pytest.LogCaptureFixture,
) -> None:
    client.post(
        "/login",
        data={
            "username": mfa_user.username,
            "password": "valid-mfa-password",
        },
    )
    current_code = pyotp.TOTP(mfa_user.mfa_secret).now()
    invalid_code = "000000" if current_code != "000000" else "000001"
    secret = mfa_user.mfa_secret
    caplog.set_level(logging.WARNING, logger=app.name)

    response = client.post("/mfa/verify", data={"code": invalid_code})
    alert = get_alerts(SecurityAlertType.MFA_FAILURE)[0]

    assert response.status_code == 200
    assert alert.user_id == mfa_user.id
    assert alert.severity == SecurityAlertSeverity.WARNING.value
    assert invalid_code not in caplog.text
    assert secret not in caplog.text
    assert "security_event=MFA_FAILURE" in caplog.text


def test_request_origin_ignores_forwarded_ip_and_sanitizes_user_agent(
    client: FlaskClient,
) -> None:
    malicious_user_agent = "demo-agent\r\ninjected-line\x00tail" + ("x" * 300)

    client.post(
        "/login",
        data={"username": "unknown.demo", "password": "invalid-password"},
        headers={"X-Forwarded-For": "198.51.100.200"},
        environ_overrides={
            "REMOTE_ADDR": "192.0.2.44",
            "HTTP_USER_AGENT": malicious_user_agent,
        },
    )
    alert = get_alerts(SecurityAlertType.LOGIN_FAILURE)[0]
    audit_log = db.session.scalar(
        db.select(AuditLog).where(
            AuditLog.event_type == AuditEventType.LOGIN_FAILURE.value
        )
    )

    assert alert.ip_address == "192.0.2.44"
    assert audit_log.ip_address == "192.0.2.44"
    assert "198.51.100.200" not in {alert.ip_address, audit_log.ip_address}
    assert "\r" not in alert.user_agent
    assert "\n" not in alert.user_agent
    assert "\x00" not in alert.user_agent
    assert len(alert.user_agent) == 255
    assert audit_log.user_agent == alert.user_agent


def test_correlation_window_creates_new_alert_after_expiration(
    app: Flask,
) -> None:
    with app.test_request_context(
        "/login", environ_overrides={"REMOTE_ADDR": "192.0.2.55"}
    ):
        first = record_security_event(
            SecurityAlertType.LOGIN_FAILURE,
            SecurityAlertSeverity.WARNING,
        )
        first.last_seen_at = datetime.now(timezone.utc) - timedelta(minutes=16)
        db.session.commit()
        second = record_security_event(
            SecurityAlertType.LOGIN_FAILURE,
            SecurityAlertSeverity.WARNING,
        )

    assert first.id != second.id
    assert len(get_alerts(SecurityAlertType.LOGIN_FAILURE)) == 2


@pytest.mark.parametrize("role", [UserRole.OPERATOR.value, UserRole.VIEWER.value])
def test_denied_admin_access_creates_warning(
    app: Flask,
    client: FlaskClient,
    active_user: User,
    role: str,
    caplog: pytest.LogCaptureFixture,
) -> None:
    active_user.role = role
    db.session.commit()
    complete_login(client, active_user.username, "valid-test-password")
    caplog.set_level(logging.WARNING, logger=app.name)

    response = client.get("/admin/users")
    alert = get_alerts(SecurityAlertType.ADMIN_ACCESS_DENIED)[0]

    assert response.status_code == 403
    assert alert.user_id == active_user.id
    assert alert.endpoint == "admin.users"
    assert "security_event=ADMIN_ACCESS_DENIED" in caplog.text


def test_generic_forbidden_response_does_not_create_security_alert(
    app: Flask, client: FlaskClient
) -> None:
    @app.get("/_test/generic-forbidden")
    def generic_forbidden():
        abort(403)

    response = client.get("/_test/generic-forbidden")

    assert response.status_code == 403
    assert db.session.scalar(
        db.select(db.func.count()).select_from(SecurityAlert)
    ) == 0


@pytest.mark.parametrize("role", [UserRole.OPERATOR.value, UserRole.VIEWER.value])
def test_non_admin_cannot_access_security_alerts(
    client: FlaskClient, active_user: User, role: str
) -> None:
    active_user.role = role
    db.session.commit()
    complete_login(client, active_user.username, "valid-test-password")

    response = client.get("/admin/security-alerts")

    assert response.status_code == 403


def test_security_alert_page_requires_authentication(client: FlaskClient) -> None:
    response = client.get("/admin/security-alerts")

    assert response.status_code == 302
    assert response.location.endswith("/login?next=%2Fadmin%2Fsecurity-alerts")


def test_admin_alert_page_orders_filters_and_paginates(
    client: FlaskClient, admin_user: User
) -> None:
    complete_login(client, admin_user.username, "valid-admin-password")
    now = datetime.now(timezone.utc)
    db.session.add_all(
        [
            SecurityAlert(
                event_type=SecurityAlertType.LOGIN_FAILURE,
                severity=SecurityAlertSeverity.WARNING,
                ip_address=f"192.0.2.{index}",
                endpoint="auth.login",
                first_seen_at=now + timedelta(minutes=index),
                last_seen_at=now + timedelta(minutes=index),
            )
            for index in range(1, 22)
        ]
    )
    db.session.add(
        SecurityAlert(
            event_type=SecurityAlertType.MFA_DECRYPTION_FAILURE,
            severity=SecurityAlertSeverity.ERROR,
            endpoint="auth.mfa_verify",
            first_seen_at=now + timedelta(minutes=30),
            last_seen_at=now + timedelta(minutes=30),
        )
    )
    db.session.commit()

    first_page = client.get("/admin/security-alerts")
    second_page = client.get("/admin/security-alerts?page=2")
    filtered = client.get("/admin/security-alerts?severity=ERROR")

    assert first_page.status_code == 200
    assert first_page.data.index(b"MFA_DECRYPTION_FAILURE") < first_page.data.index(
        b"192.0.2.21"
    )
    assert b"192.0.2.1</td>" not in first_page.data
    assert b"192.0.2.1</td>" in second_page.data
    assert b"192.0.2.21</td>" not in filtered.data
    assert b"MFA_DECRYPTION_FAILURE" in filtered.data
    assert client.get("/admin/security-alerts?page=999").status_code == 404


def test_admin_can_review_alert_and_action_is_audited(
    client: FlaskClient, admin_user: User
) -> None:
    alert = SecurityAlert(
        event_type=SecurityAlertType.LOGIN_FAILURE,
        severity=SecurityAlertSeverity.WARNING,
    )
    db.session.add(alert)
    db.session.commit()
    complete_login(client, admin_user.username, "valid-admin-password")

    response = client.post(f"/admin/security-alerts/{alert.id}/review")
    db.session.refresh(alert)
    audit_log = db.session.scalar(
        db.select(AuditLog).where(
            AuditLog.event_type == AuditEventType.SECURITY_ALERT_REVIEWED.value
        )
    )

    assert response.status_code == 302
    assert alert.status == SecurityAlertStatus.REVIEWED.value
    assert alert.reviewed_by_user_id == admin_user.id
    assert alert.reviewed_at is not None
    assert audit_log.actor_user_id == admin_user.id
    assert audit_log.resource_type == "security_alert"
    assert audit_log.resource_id == alert.id


def test_mfa_decryption_failure_is_persisted_as_error_without_secret(
    app: Flask,
    client: FlaskClient,
    mfa_user: User,
    caplog: pytest.LogCaptureFixture,
) -> None:
    secret = mfa_user.mfa_secret
    wrong_key = Fernet.generate_key().decode("ascii")
    app.config["MFA_ENCRYPTION_KEY"] = wrong_key
    app.config["PROPAGATE_EXCEPTIONS"] = False
    caplog.set_level(logging.ERROR, logger=app.name)

    response = client.post(
        "/login",
        data={
            "username": mfa_user.username,
            "password": "valid-mfa-password",
        },
    )
    alert = get_alerts(SecurityAlertType.MFA_DECRYPTION_FAILURE)[0]

    assert response.status_code == 500
    assert alert.severity == SecurityAlertSeverity.ERROR.value
    assert alert.user_id == mfa_user.id
    assert secret not in caplog.text
    assert wrong_key not in caplog.text
    assert secret.encode() not in response.data
    assert wrong_key.encode() not in response.data


def test_internal_auth_error_is_persisted_without_exposing_exception(
    app: Flask,
    client: FlaskClient,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    app.config["PROPAGATE_EXCEPTIONS"] = False

    def fail_password_check(*_args, **_kwargs):
        raise RuntimeError("private database diagnostic")

    monkeypatch.setattr("app.auth.routes.verify_user_password", fail_password_check)

    response = client.post(
        "/login",
        data={"username": "unknown.demo", "password": "private-password"},
    )
    alert = get_alerts(SecurityAlertType.INTERNAL_AUTH_ERROR)[0]

    assert response.status_code == 500
    assert alert.severity == SecurityAlertSeverity.ERROR.value
    assert b"private database diagnostic" not in response.data
    assert b"private-password" not in response.data


def test_security_alert_persistence_failure_is_logged_safely(
    app: Flask,
    monkeypatch: pytest.MonkeyPatch,
    caplog: pytest.LogCaptureFixture,
) -> None:
    def fail_commit() -> None:
        raise OperationalError("private insert", {}, Exception("database unavailable"))

    monkeypatch.setattr(db.session, "commit", fail_commit)
    caplog.set_level(logging.ERROR, logger=app.name)

    result = record_security_event(
        SecurityAlertType.LOGIN_FAILURE,
        SecurityAlertSeverity.WARNING,
    )

    assert result is None
    assert "security_alert_persistence_failed" in caplog.text
    assert "private insert" not in caplog.text
