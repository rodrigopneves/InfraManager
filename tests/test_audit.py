import json
import logging
from datetime import datetime, timedelta, timezone
from urllib.parse import urlparse

import pyotp
import pytest
from flask.testing import FlaskClient
from sqlalchemy.exc import OperationalError

from app.account.routes import MFA_SETUP_SECRET_KEY
from app.audit import record_event
from app.extensions import db
from app.models import AuditEventType, AuditLog, User, UserRole


def post_login(
    client: FlaskClient,
    username: str,
    password: str,
    **kwargs,
):
    return client.post(
        "/login",
        data={"username": username, "password": password},
        **kwargs,
    )


def login_admin(client: FlaskClient) -> None:
    response = post_login(client, "admin.demo", "valid-admin-password")
    assert urlparse(response.location).path == "/dashboard"


def complete_mfa_login(client: FlaskClient, user: User) -> str:
    response = post_login(client, user.username, "valid-mfa-password")
    assert urlparse(response.location).path == "/mfa/verify"
    code = pyotp.TOTP(user.mfa_secret).now()
    response = client.post("/mfa/verify", data={"code": code})
    assert urlparse(response.location).path == "/dashboard"
    return code


def get_events(event_type: AuditEventType) -> list[AuditLog]:
    return db.session.scalars(
        db.select(AuditLog)
        .where(AuditLog.event_type == event_type.value)
        .order_by(AuditLog.id)
    ).all()


def test_successful_login_records_event_with_ip_and_limited_user_agent(
    client: FlaskClient, active_user: User
) -> None:
    long_user_agent = "test-agent/" + ("x" * 400)

    response = post_login(
        client,
        active_user.username,
        "valid-test-password",
        environ_overrides={"REMOTE_ADDR": "203.0.113.25"},
        headers={"User-Agent": long_user_agent},
    )
    audit_log = get_events(AuditEventType.LOGIN_SUCCESS)[0]

    assert response.status_code == 302
    assert audit_log.actor_user_id == active_user.id
    assert audit_log.target_user_id is None
    assert audit_log.ip_address == "203.0.113.25"
    assert audit_log.user_agent == long_user_agent[:255]
    assert len(audit_log.user_agent) == 255
    assert audit_log.details == {}


def test_failed_login_records_generic_event_without_credentials(
    client: FlaskClient, active_user: User
) -> None:
    submitted_password = "password-that-must-not-be-audited"
    csrf_value = "csrf-value-that-must-not-be-audited"

    response = client.post(
        "/login",
        data={
            "username": active_user.username,
            "password": submitted_password,
            "csrf_token": csrf_value,
        },
    )
    audit_log = get_events(AuditEventType.LOGIN_FAILURE)[0]
    serialized_log = json.dumps(audit_log.details)

    assert response.status_code == 200
    assert audit_log.actor_user_id is None
    assert audit_log.target_user_id is None
    assert audit_log.details == {"reason": "authentication_failed"}
    assert submitted_password not in serialized_log
    assert csrf_value not in serialized_log
    assert active_user.password_hash not in serialized_log


def test_mfa_success_and_login_success_only_follow_second_factor(
    client: FlaskClient, mfa_user: User
) -> None:
    first_factor = post_login(client, mfa_user.username, "valid-mfa-password")

    assert urlparse(first_factor.location).path == "/mfa/verify"
    assert get_events(AuditEventType.MFA_SUCCESS) == []
    assert get_events(AuditEventType.LOGIN_SUCCESS) == []

    code = pyotp.TOTP(mfa_user.mfa_secret).now()
    second_factor = client.post("/mfa/verify", data={"code": code})

    assert urlparse(second_factor.location).path == "/dashboard"
    assert len(get_events(AuditEventType.MFA_SUCCESS)) == 1
    assert len(get_events(AuditEventType.LOGIN_SUCCESS)) == 1
    serialized_logs = json.dumps(
        [audit_log.details for audit_log in db.session.scalars(db.select(AuditLog))]
    )
    assert code not in serialized_logs
    assert mfa_user.mfa_secret not in serialized_logs


def test_invalid_mfa_records_failure_without_code(
    client: FlaskClient, mfa_user: User
) -> None:
    post_login(client, mfa_user.username, "valid-mfa-password")
    current_code = pyotp.TOTP(mfa_user.mfa_secret).now()
    invalid_code = "000000" if current_code != "000000" else "000001"

    response = client.post("/mfa/verify", data={"code": invalid_code})
    audit_log = get_events(AuditEventType.MFA_FAILURE)[0]

    assert response.status_code == 200
    assert audit_log.actor_user_id is None
    assert audit_log.target_user_id == mfa_user.id
    assert invalid_code not in json.dumps(audit_log.details)
    assert get_events(AuditEventType.LOGIN_SUCCESS) == []


def test_logout_records_authenticated_actor(
    client: FlaskClient, active_user: User
) -> None:
    post_login(client, active_user.username, "valid-test-password")

    response = client.post("/logout")
    audit_log = get_events(AuditEventType.LOGOUT)[0]

    assert urlparse(response.location).path == "/login"
    assert audit_log.actor_user_id == active_user.id


def test_enabling_mfa_records_event_without_secret_or_code(
    client: FlaskClient, active_user: User
) -> None:
    post_login(client, active_user.username, "valid-test-password")
    client.get("/account/mfa/setup")
    with client.session_transaction() as session:
        secret = session[MFA_SETUP_SECRET_KEY]
    code = pyotp.TOTP(secret).now()

    response = client.post("/account/mfa/setup", data={"code": code})
    audit_log = get_events(AuditEventType.MFA_ENABLED)[0]
    serialized_log = json.dumps(audit_log.details)

    assert urlparse(response.location).path == "/dashboard"
    assert audit_log.actor_user_id == active_user.id
    assert audit_log.target_user_id == active_user.id
    assert secret not in serialized_log
    assert code not in serialized_log


def test_disabling_mfa_records_event_and_no_sensitive_data(
    client: FlaskClient, mfa_user: User
) -> None:
    complete_mfa_login(client, mfa_user)
    secret = mfa_user.mfa_secret
    code = pyotp.TOTP(secret).now()

    response = client.post(
        "/account/mfa/disable",
        data={"password": "valid-mfa-password", "code": code},
    )
    audit_log = get_events(AuditEventType.MFA_DISABLED)[0]
    serialized_log = json.dumps(audit_log.details)

    assert urlparse(response.location).path == "/dashboard"
    assert audit_log.actor_user_id == mfa_user.id
    assert audit_log.target_user_id == mfa_user.id
    assert secret not in serialized_log
    assert code not in serialized_log
    assert "valid-mfa-password" not in serialized_log


def test_user_creation_records_actor_target_role_and_status(
    client: FlaskClient, admin_user: User
) -> None:
    login_admin(client)

    response = client.post(
        "/admin/users/new",
        data={
            "username": "audited.user",
            "email": "audited.user@example.com",
            "password": "new-user-password",
            "password_confirmation": "new-user-password",
            "is_active": "y",
            "role": UserRole.OPERATOR.value,
        },
    )
    created_user = db.session.scalar(
        db.select(User).where(User.username == "audited.user")
    )
    audit_log = get_events(AuditEventType.USER_CREATED)[0]

    assert response.status_code == 302
    assert audit_log.actor_user_id == admin_user.id
    assert audit_log.target_user_id == created_user.id
    assert audit_log.details == {"role": "operator", "is_active": True}
    assert "new-user-password" not in json.dumps(audit_log.details)


def test_user_edit_and_role_change_record_controlled_events(
    client: FlaskClient, admin_user: User, regular_user: User
) -> None:
    login_admin(client)

    response = client.post(
        f"/admin/users/{regular_user.id}/edit",
        data={
            "username": regular_user.username,
            "email": "changed.audit@example.com",
            "is_active": "y",
            "role": UserRole.OPERATOR.value,
        },
    )
    update_log = get_events(AuditEventType.USER_UPDATED)[0]
    role_log = get_events(AuditEventType.USER_ROLE_CHANGED)[0]

    assert response.status_code == 302
    assert update_log.actor_user_id == admin_user.id
    assert update_log.target_user_id == regular_user.id
    assert update_log.details == {"changed_fields": ["email", "role"]}
    assert role_log.details == {"old_role": "viewer", "new_role": "operator"}


def test_user_deactivation_and_activation_record_separate_events(
    client: FlaskClient, admin_user: User, regular_user: User
) -> None:
    login_admin(client)
    url = f"/admin/users/{regular_user.id}/toggle-active"

    client.post(url)
    client.post(url)

    deactivated = get_events(AuditEventType.USER_DEACTIVATED)[0]
    activated = get_events(AuditEventType.USER_ACTIVATED)[0]
    assert deactivated.actor_user_id == admin_user.id
    assert deactivated.target_user_id == regular_user.id
    assert activated.actor_user_id == admin_user.id
    assert activated.target_user_id == regular_user.id


def test_audit_service_rejects_unapproved_or_arbitrary_details(app) -> None:
    with pytest.raises(ValueError, match="unsupported fields"):
        record_event(
            AuditEventType.LOGIN_FAILURE,
            details={"password_hash": "must-not-be-recorded"},
        )

    with pytest.raises(ValueError, match="invalid"):
        record_event(
            AuditEventType.USER_CREATED,
            details={"role": {"arbitrary": "object"}},
        )

    assert db.session.scalar(db.select(db.func.count()).select_from(AuditLog)) == 0


def test_audit_database_failure_is_reported_without_breaking_caller(
    app, monkeypatch: pytest.MonkeyPatch, caplog: pytest.LogCaptureFixture
) -> None:
    def fail_commit() -> None:
        raise OperationalError("audit insert", {}, Exception("database unavailable"))

    monkeypatch.setattr(db.session, "commit", fail_commit)
    caplog.set_level(logging.ERROR, logger=app.name)

    result = record_event(
        AuditEventType.LOGIN_FAILURE,
        details={"reason": "authentication_failed"},
    )

    assert result is None
    assert "Failed to persist audit event LOGIN_FAILURE." in caplog.text
    assert "authentication_failed" not in caplog.text
    assert "audit insert" not in caplog.text


@pytest.mark.parametrize("role", [UserRole.OPERATOR.value, UserRole.VIEWER.value])
def test_non_admin_cannot_access_audit_page(
    role: str, client: FlaskClient, active_user: User
) -> None:
    active_user.role = role
    db.session.commit()
    post_login(client, active_user.username, "valid-test-password")

    response = client.get("/admin/audit")

    assert response.status_code == 403


def test_admin_can_access_audit_page(
    client: FlaskClient, admin_user: User
) -> None:
    login_admin(client)

    response = client.get("/admin/audit")

    assert response.status_code == 200
    assert b"LOGIN_SUCCESS" in response.data
    assert admin_user.username.encode() in response.data


def test_audit_page_orders_newest_events_first(
    client: FlaskClient, admin_user: User
) -> None:
    login_admin(client)
    db.session.execute(db.delete(AuditLog))
    now = datetime.now(timezone.utc)
    db.session.add_all(
        [
            AuditLog(
                event_type=AuditEventType.LOGIN_FAILURE,
                details={"reason": "authentication_failed"},
                created_at=now - timedelta(minutes=1),
            ),
            AuditLog(
                event_type=AuditEventType.LOGOUT,
                details={},
                created_at=now,
            ),
        ]
    )
    db.session.commit()

    response = client.get("/admin/audit")

    assert response.status_code == 200
    assert response.data.index(b"LOGOUT") < response.data.index(b"LOGIN_FAILURE")


def test_audit_page_paginates_twenty_entries_and_orders_between_pages(
    client: FlaskClient, admin_user: User
) -> None:
    login_admin(client)
    db.session.execute(db.delete(AuditLog))
    now = datetime.now(timezone.utc)
    db.session.add_all(
        [
            AuditLog(
                event_type=AuditEventType.LOGIN_FAILURE,
                ip_address=f"192.0.2.{index}",
                details={"reason": "authentication_failed"},
                created_at=now + timedelta(minutes=index),
            )
            for index in range(1, 22)
        ]
    )
    db.session.commit()

    first_page = client.get("/admin/audit")
    second_page = client.get("/admin/audit?page=2")

    assert first_page.status_code == 200
    assert first_page.data.count(b"<tr>") == 21
    assert b"192.0.2.21" in first_page.data
    assert b"192.0.2.1</td>" not in first_page.data
    assert first_page.data.index(b"192.0.2.21") < first_page.data.index(
        b"192.0.2.20"
    )
    assert "Próxima".encode() in first_page.data
    assert "Anterior".encode() not in first_page.data

    assert second_page.status_code == 200
    assert second_page.data.count(b"<tr>") == 2
    assert b"192.0.2.1</td>" in second_page.data
    assert b"192.0.2.21" not in second_page.data
    assert "Anterior".encode() in second_page.data
    assert "Próxima".encode() not in second_page.data
    assert client.get("/admin/audit?page=999").status_code == 404


def test_paginated_audit_keeps_actor_target_and_resource_fields(
    client: FlaskClient, admin_user: User, active_user: User
) -> None:
    login_admin(client)
    db.session.execute(db.delete(AuditLog))
    db.session.add(
        AuditLog(
            event_type=AuditEventType.VM_CREATE,
            actor_user_id=admin_user.id,
            target_user_id=active_user.id,
            ip_address="198.51.100.10",
            details={},
            resource_type="virtual_machine",
            resource_id=77,
            result="success",
        )
    )
    db.session.commit()

    response = client.get("/admin/audit")

    assert response.status_code == 200
    assert admin_user.username.encode() in response.data
    assert active_user.username.encode() in response.data
    assert b"198.51.100.10" in response.data
    assert b"virtual_machine #77" in response.data
    assert b"success" in response.data


def test_create_admin_cli_records_event_without_actor(app) -> None:
    result = app.test_cli_runner().invoke(
        args=["create-admin"],
        input=(
            "audit.cli\n"
            "audit.cli@example.com\n"
            "cli-admin-password\n"
            "cli-admin-password\n"
        ),
    )
    created_user = db.session.scalar(
        db.select(User).where(User.username == "audit.cli")
    )
    audit_log = get_events(AuditEventType.USER_CREATED)[0]

    assert result.exit_code == 0
    assert audit_log.actor_user_id is None
    assert audit_log.target_user_id == created_user.id
    assert audit_log.details == {
        "role": "admin",
        "is_active": True,
        "source": "cli",
    }
    assert "cli-admin-password" not in json.dumps(audit_log.details)
