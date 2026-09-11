from flask.testing import FlaskClient

from app.models import User
from tests.helpers import complete_login


def test_index_redirects_anonymous_user_to_login(client: FlaskClient) -> None:
    response = client.get("/")

    assert response.status_code == 302
    assert response.location == "/login"


def test_index_redirects_authenticated_user_to_dashboard(
    client: FlaskClient, active_user: User
) -> None:
    complete_login(client, active_user.username, "valid-test-password")

    response = client.get("/")

    assert response.status_code == 302
    assert response.location == "/dashboard"


def test_index_redirects_pending_mfa_user_to_login(
    client: FlaskClient, active_user: User
) -> None:
    first_factor = client.post(
        "/login",
        data={"username": active_user.username, "password": "valid-test-password"},
    )
    assert first_factor.status_code == 302
    assert first_factor.location == "/mfa/verify"

    response = client.get("/")

    assert response.status_code == 302
    assert response.location == "/login"
    with client.session_transaction() as session:
        assert "_user_id" not in session


def test_health_returns_ok(client: FlaskClient) -> None:
    response = client.get("/health")

    assert response.status_code == 200
    assert response.get_json() == {"status": "ok"}
