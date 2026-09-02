from urllib.parse import urlparse

from flask.testing import FlaskClient

from app import create_app
from app.extensions import db
from app.models import User
from config import TestingConfig


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


def test_invalid_password_is_rejected(
    client: FlaskClient, active_user: User
) -> None:
    response = submit_login(client, password="incorrect-password")

    assert response.status_code == 200
    assert "Usuário ou senha inválidos.".encode() in response.data


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

    assert login_response.status_code == 400
    assert logout_response.status_code == 400
