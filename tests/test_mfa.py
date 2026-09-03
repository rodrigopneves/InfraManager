import time
from urllib.parse import urlparse

import pyotp
from flask import Flask
from flask.testing import FlaskClient

from app.account.routes import MFA_SETUP_SECRET_KEY
from app.auth.services import (
    PENDING_MFA_STARTED_AT_KEY,
    PENDING_MFA_USER_ID_KEY,
)
from app.extensions import db
from app.models import User


def login_with_password(
    client: FlaskClient,
    username: str = "mfa.demo",
    password: str = "valid-mfa-password",
):
    return client.post(
        "/login", data={"username": username, "password": password}
    )


def invalid_totp_for(secret: str) -> str:
    current_code = pyotp.TOTP(secret).now()
    return "000000" if current_code != "000000" else "000001"


def complete_mfa_login(client: FlaskClient, user: User):
    first_response = login_with_password(client, user.username, "valid-mfa-password")
    assert urlparse(first_response.location).path == "/mfa/verify"
    return client.post(
        "/mfa/verify", data={"code": pyotp.TOTP(user.mfa_secret).now()}
    )


def test_user_without_mfa_still_logs_in_with_password(
    client: FlaskClient, active_user: User
) -> None:
    response = client.post(
        "/login",
        data={"username": active_user.username, "password": "valid-test-password"},
    )

    assert urlparse(response.location).path == "/dashboard"
    assert client.get("/dashboard").status_code == 200


def test_mfa_user_requires_verification_before_authentication(
    client: FlaskClient, mfa_user: User
) -> None:
    response = login_with_password(client)

    assert response.status_code == 302
    assert urlparse(response.location).path == "/mfa/verify"
    verify_response = client.get("/mfa/verify")
    assert verify_response.headers["Cache-Control"] == "no-store"
    dashboard_response = client.get("/dashboard")
    assert dashboard_response.status_code == 302
    assert urlparse(dashboard_response.location).path == "/login"


def test_valid_totp_completes_login_and_clears_pending_state(
    client: FlaskClient, mfa_user: User
) -> None:
    login_with_password(client)
    response = client.post(
        "/mfa/verify",
        data={"code": pyotp.TOTP(mfa_user.mfa_secret).now()},
    )

    assert urlparse(response.location).path == "/dashboard"
    assert client.get("/dashboard").status_code == 200
    with client.session_transaction() as session:
        assert PENDING_MFA_USER_ID_KEY not in session
        assert PENDING_MFA_STARTED_AT_KEY not in session


def test_invalid_totp_does_not_authenticate(
    client: FlaskClient, mfa_user: User
) -> None:
    login_with_password(client)
    invalid_code = invalid_totp_for(mfa_user.mfa_secret)
    response = client.post("/mfa/verify", data={"code": invalid_code})

    assert "Código de autenticação inválido.".encode() in response.data
    assert invalid_code.encode() not in response.data
    assert client.get("/dashboard").status_code == 302


def test_malformed_totp_is_rejected_without_echoing_it(
    client: FlaskClient, mfa_user: User
) -> None:
    login_with_password(client)

    response = client.post("/mfa/verify", data={"code": "12ab56"})

    assert response.status_code == 200
    assert "Código de autenticação inválido.".encode() in response.data
    assert b"12ab56" not in response.data
    assert client.get("/dashboard").status_code == 302


def test_mfa_verify_without_pending_state_redirects_to_login(
    client: FlaskClient,
) -> None:
    response = client.get("/mfa/verify")

    assert response.status_code == 302
    assert urlparse(response.location).path == "/login"
    assert client.get("/dashboard").status_code == 302


def test_pending_mfa_state_expires_and_is_removed(
    client: FlaskClient, mfa_user: User
) -> None:
    login_with_password(client)
    with client.session_transaction() as session:
        session[PENDING_MFA_STARTED_AT_KEY] = int(time.time()) - 301

    response = client.post(
        "/mfa/verify", data={"code": pyotp.TOTP(mfa_user.mfa_secret).now()}
    )

    assert urlparse(response.location).path == "/login"
    assert client.get("/dashboard").status_code == 302
    with client.session_transaction() as session:
        assert PENDING_MFA_USER_ID_KEY not in session
        assert PENDING_MFA_STARTED_AT_KEY not in session


def test_pending_session_contains_only_user_id_and_timestamp(
    client: FlaskClient, mfa_user: User
) -> None:
    code = pyotp.TOTP(mfa_user.mfa_secret).now()
    login_with_password(client)

    with client.session_transaction() as session:
        assert set(session) == {
            PENDING_MFA_USER_ID_KEY,
            PENDING_MFA_STARTED_AT_KEY,
        }
        serialized_values = " ".join(str(value) for value in session.values())

    assert "valid-mfa-password" not in serialized_values
    assert mfa_user.mfa_secret not in serialized_values
    assert code not in serialized_values


def test_inactive_user_between_factors_cannot_authenticate(
    client: FlaskClient, mfa_user: User
) -> None:
    login_with_password(client)
    mfa_user.is_active = False
    db.session.commit()

    response = client.post(
        "/mfa/verify", data={"code": pyotp.TOTP(mfa_user.mfa_secret).now()}
    )

    assert urlparse(response.location).path == "/login"
    assert client.get("/dashboard").status_code == 302
    with client.session_transaction() as session:
        assert PENDING_MFA_USER_ID_KEY not in session


def test_inconsistent_enabled_mfa_never_bypasses_second_factor(
    client: FlaskClient, mfa_user: User
) -> None:
    mfa_user.mfa_secret = None
    db.session.commit()

    response = login_with_password(client)

    assert response.status_code == 200
    assert client.get("/dashboard").status_code == 302


def test_setup_requires_authentication_and_qr_is_not_public(
    client: FlaskClient,
) -> None:
    response = client.get("/account/mfa/setup")

    assert response.status_code == 302
    assert urlparse(response.location).path == "/login"
    assert client.get("/account/mfa/qr").status_code == 404


def test_opening_setup_creates_qr_but_does_not_enable_mfa(
    client: FlaskClient, active_user: User
) -> None:
    client.post(
        "/login",
        data={"username": active_user.username, "password": "valid-test-password"},
    )
    response = client.get("/account/mfa/setup")
    db.session.refresh(active_user)

    assert response.status_code == 200
    assert b"data:image/svg+xml;base64," in response.data
    assert response.headers["Cache-Control"] == "no-store"
    assert active_user.mfa_enabled is False
    assert active_user.mfa_secret is None


def test_valid_setup_code_enables_mfa_and_removes_pending_secret(
    client: FlaskClient, active_user: User
) -> None:
    client.post(
        "/login",
        data={"username": active_user.username, "password": "valid-test-password"},
    )
    setup_response = client.get("/account/mfa/setup")
    with client.session_transaction() as session:
        secret = session[MFA_SETUP_SECRET_KEY]

    response = client.post(
        "/account/mfa/setup", data={"code": pyotp.TOTP(secret).now()}
    )
    db.session.refresh(active_user)

    assert setup_response.status_code == 200
    assert secret.encode() not in setup_response.data
    assert urlparse(response.location).path == "/dashboard"
    assert active_user.mfa_enabled is True
    assert active_user.mfa_secret == secret
    with client.session_transaction() as session:
        assert MFA_SETUP_SECRET_KEY not in session


def test_invalid_setup_code_does_not_enable_mfa(
    client: FlaskClient, active_user: User
) -> None:
    client.post(
        "/login",
        data={"username": active_user.username, "password": "valid-test-password"},
    )
    client.get("/account/mfa/setup")

    with client.session_transaction() as session:
        secret = session[MFA_SETUP_SECRET_KEY]
    invalid_code = invalid_totp_for(secret)
    response = client.post("/account/mfa/setup", data={"code": invalid_code})
    db.session.refresh(active_user)

    assert "Código de autenticação inválido.".encode() in response.data
    assert invalid_code.encode() not in response.data
    assert active_user.mfa_enabled is False
    assert active_user.mfa_secret is None


def test_cancel_setup_removes_pending_secret(
    client: FlaskClient, active_user: User
) -> None:
    client.post(
        "/login",
        data={"username": active_user.username, "password": "valid-test-password"},
    )
    client.get("/account/mfa/setup")

    response = client.post("/account/mfa/setup/cancel")

    assert urlparse(response.location).path == "/dashboard"
    with client.session_transaction() as session:
        assert MFA_SETUP_SECRET_KEY not in session


def test_user_can_disable_mfa_with_password_and_totp(
    client: FlaskClient, mfa_user: User
) -> None:
    complete_mfa_login(client, mfa_user)

    response = client.post(
        "/account/mfa/disable",
        data={
            "password": "valid-mfa-password",
            "code": pyotp.TOTP(mfa_user.mfa_secret).now(),
        },
    )
    db.session.refresh(mfa_user)

    assert urlparse(response.location).path == "/dashboard"
    assert mfa_user.mfa_enabled is False
    assert mfa_user.mfa_secret is None


def test_wrong_password_prevents_mfa_disable(
    client: FlaskClient, mfa_user: User
) -> None:
    complete_mfa_login(client, mfa_user)
    original_secret = mfa_user.mfa_secret

    response = client.post(
        "/account/mfa/disable",
        data={
            "password": "wrong-password",
            "code": pyotp.TOTP(original_secret).now(),
        },
        follow_redirects=True,
    )
    db.session.refresh(mfa_user)

    assert "Não foi possível desativar o MFA.".encode() in response.data
    assert mfa_user.mfa_enabled is True
    assert mfa_user.mfa_secret == original_secret


def test_wrong_totp_prevents_mfa_disable(
    client: FlaskClient, mfa_user: User
) -> None:
    complete_mfa_login(client, mfa_user)
    original_secret = mfa_user.mfa_secret

    invalid_code = invalid_totp_for(original_secret)
    response = client.post(
        "/account/mfa/disable",
        data={"password": "valid-mfa-password", "code": invalid_code},
    )
    db.session.refresh(mfa_user)

    assert "Não foi possível desativar o MFA.".encode() in response.data
    assert invalid_code.encode() not in response.data
    assert mfa_user.mfa_enabled is True
    assert mfa_user.mfa_secret == original_secret


def test_admin_list_shows_only_mfa_status(
    client: FlaskClient, admin_user: User
) -> None:
    admin_user.mfa_enabled = True
    admin_user.mfa_secret = pyotp.random_base32()
    db.session.commit()
    secret = admin_user.mfa_secret

    client.post(
        "/login",
        data={"username": admin_user.username, "password": "valid-admin-password"},
    )
    client.post(
        "/mfa/verify", data={"code": pyotp.TOTP(secret).now()}
    )
    response = client.get("/admin/users")

    assert response.status_code == 200
    assert b"MFA" in response.data
    assert b"Ativo" in response.data
    assert secret.encode() not in response.data


def test_client_tampering_with_signed_pending_session_does_not_authenticate(
    app: Flask, client: FlaskClient, mfa_user: User
) -> None:
    login_with_password(client)
    cookie_name = app.config["SESSION_COOKIE_NAME"]
    cookie = client.get_cookie(cookie_name)
    assert cookie is not None
    change_index = len(cookie.value) // 2
    replacement = "a" if cookie.value[change_index] != "a" else "b"
    tampered_cookie = (
        cookie.value[:change_index]
        + replacement
        + cookie.value[change_index + 1 :]
    )
    client.set_cookie(cookie_name, tampered_cookie)

    response = client.post(
        "/mfa/verify", data={"code": pyotp.TOTP(mfa_user.mfa_secret).now()}
    )

    assert urlparse(response.location).path == "/login"
    assert client.get("/dashboard").status_code == 302
