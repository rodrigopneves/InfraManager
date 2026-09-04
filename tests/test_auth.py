from urllib.parse import urlparse

import pytest
from flask.testing import FlaskClient

from app import create_app
from app.extensions import db
from app.models import User
from config import Config, ProductionConfig, TestingConfig


def submit_login(
    client: FlaskClient,
    username: str = "login.demo",
    password: str = "valid-test-password",
    *,
    follow_redirects: bool = False,
):
    return client.post(
        "/login",
        data={"username": username, "password": password},
        follow_redirects=follow_redirects,
    )


def test_login_page_is_accessible(client: FlaskClient) -> None:
    response = client.get("/login")

    assert response.status_code == 200
    assert b'name="username"' in response.data
    assert b'name="password"' in response.data


def test_valid_credentials_authenticate_user(
    client: FlaskClient, active_user: User
) -> None:
    response = submit_login(client, follow_redirects=True)

    assert response.status_code == 200
    assert b"Bem-vindo, login.demo." in response.data


@pytest.mark.parametrize("username", ["  login.demo  ", "LOGIN.DEMO"])
def test_login_normalizes_username(
    client: FlaskClient, active_user: User, username: str
) -> None:
    response = submit_login(client, username=username, follow_redirects=True)

    assert response.status_code == 200
    assert b"Bem-vindo, login.demo." in response.data


def test_invalid_password_is_rejected(
    client: FlaskClient, active_user: User
) -> None:
    response = submit_login(client, password="incorrect-password")

    assert response.status_code == 200
    assert "Usuário ou senha inválidos.".encode() in response.data
    assert b"incorrect-password" not in response.data


def test_unknown_username_is_rejected(client: FlaskClient) -> None:
    response = submit_login(client, username="unknown.demo")

    assert response.status_code == 200
    assert "Usuário ou senha inválidos.".encode() in response.data


def test_inactive_user_is_rejected(
    client: FlaskClient, active_user: User
) -> None:
    active_user.is_active = False
    db.session.commit()

    response = submit_login(client)

    assert response.status_code == 200
    assert "Usuário ou senha inválidos.".encode() in response.data


def test_unauthenticated_user_is_redirected_to_login(client: FlaskClient) -> None:
    response = client.get("/dashboard")

    assert response.status_code == 302
    assert urlparse(response.location).path == "/login"


def test_authenticated_user_can_access_dashboard(
    client: FlaskClient, active_user: User
) -> None:
    submit_login(client)

    response = client.get("/dashboard")

    assert response.status_code == 200
    assert b"Bem-vindo, login.demo." in response.data


def test_logout_ends_authenticated_session(
    client: FlaskClient, active_user: User
) -> None:
    submit_login(client)

    logout_response = client.post("/logout")
    dashboard_response = client.get("/dashboard")

    assert logout_response.status_code == 302
    assert urlparse(logout_response.location).path == "/login"
    assert dashboard_response.status_code == 302
    assert urlparse(dashboard_response.location).path == "/login"


def test_authenticated_user_is_redirected_away_from_login(
    client: FlaskClient, active_user: User
) -> None:
    submit_login(client)

    response = client.get("/login")

    assert response.status_code == 302
    assert urlparse(response.location).path == "/dashboard"


def test_csrf_is_enabled_outside_default_test_configuration() -> None:
    class CsrfEnabledTestingConfig(TestingConfig):
        SECRET_KEY = "csrf-test-only-secret-key"
        WTF_CSRF_ENABLED = True

    app = create_app(CsrfEnabledTestingConfig)
    client = app.test_client()
    login_response = client.post(
        "/login",
        data={"username": "login.demo", "password": "valid-test-password"},
    )
    logout_response = client.post("/logout")
    mfa_response = client.post("/mfa/verify", data={"code": "123456"})
    setup_response = client.post("/account/mfa/setup", data={"code": "123456"})
    disable_response = client.post(
        "/account/mfa/disable",
        data={"password": "not-a-real-password", "code": "123456"},
    )

    assert login_response.status_code == 400
    assert logout_response.status_code == 400
    assert mfa_response.status_code == 400
    assert setup_response.status_code == 400
    assert disable_response.status_code == 400
    expected_message = (
        "A solicitação não pôde ser validada. "
        "Atualize a página e tente novamente."
    ).encode()
    assert expected_message in login_response.data
    assert b"csrf" not in login_response.data.lower()
    assert b"token" not in login_response.data.lower()


def test_session_cookie_and_secret_key_configuration() -> None:
    assert Config.SESSION_COOKIE_HTTPONLY is True
    assert Config.SESSION_COOKIE_SAMESITE == "Lax"
    assert Config.SESSION_PERMANENT is False
    assert ProductionConfig.SESSION_COOKIE_SECURE is True
    assert TestingConfig.SECRET_KEY == "testing-only-secret-key"
    assert ProductionConfig.SECRET_KEY == Config.SECRET_KEY


def test_production_requires_secret_key(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setattr(
        ProductionConfig, "SQLALCHEMY_DATABASE_URI", "sqlite:///:memory:"
    )
    monkeypatch.setattr(ProductionConfig, "SECRET_KEY", None)

    with pytest.raises(RuntimeError, match="SECRET_KEY"):
        create_app("production")


@pytest.mark.parametrize(
    "path",
    [
        "/logout",
        "/mfa/verify",
        "/account/mfa/setup",
        "/account/mfa/setup/cancel",
        "/account/mfa/disable",
        "/admin/users/new",
        "/admin/users/1/edit",
        "/admin/users/1/toggle-active",
        "/datacenters/create",
        "/datacenters/1/edit",
        "/datacenters/1/delete",
        "/rooms/create",
        "/rooms/1/edit",
        "/rooms/1/delete",
        "/racks/create",
        "/racks/1/edit",
        "/racks/1/delete",
    ],
)
def test_mutating_routes_reject_missing_csrf_token(path: str) -> None:
    class CsrfEnabledTestingConfig(TestingConfig):
        SECRET_KEY = "csrf-routes-test-only-secret-key"
        WTF_CSRF_ENABLED = True

    application = create_app(CsrfEnabledTestingConfig)
    response = application.test_client().post(path)

    assert response.status_code == 400
