from flask.testing import FlaskClient

from app.models import Asset, User


def login(client: FlaskClient, user: User, password: str) -> None:
    response = client.post(
        "/login",
        data={"username": user.username, "password": password},
    )
    assert response.status_code == 302


def test_public_layout_loads_bootstrap_and_custom_styles(
    client: FlaskClient,
) -> None:
    response = client.get("/")

    assert response.status_code == 200
    assert b"bootstrap@5.3.3" in response.data
    assert b'/static/css/app.css' in response.data
    assert b'aria-label="Navega\xc3\xa7\xc3\xa3o principal"' in response.data
    assert b'href="/login"' in response.data


def test_authenticated_layout_has_navigation_user_and_csrf_logout(
    client: FlaskClient,
    viewer_user: User,
) -> None:
    login(client, viewer_user, "valid-viewer-password")

    response = client.get("/dashboard")

    assert response.status_code == 200
    assert b'href="/dashboard"' in response.data
    assert b'href="/datacenters"' in response.data
    assert b'href="/rooms"' in response.data
    assert b'href="/racks"' in response.data
    assert b'href="/assets"' in response.data
    assert b'href="/virtual-machines"' in response.data
    assert viewer_user.username.encode() in response.data
    assert viewer_user.role_label.encode() in response.data
    assert b'action="/logout"' in response.data
    assert b'name="csrf_token"' in response.data


def test_administrative_navigation_is_visible_only_to_admin(
    client: FlaskClient,
    viewer_user: User,
    admin_user: User,
) -> None:
    login(client, viewer_user, "valid-viewer-password")
    viewer_response = client.get("/dashboard")
    client.post("/logout")

    login(client, admin_user, "valid-admin-password")
    admin_response = client.get("/dashboard")

    assert b'href="/admin/users"' not in viewer_response.data
    assert b'href="/admin/audit"' not in viewer_response.data
    assert b'href="/admin/users"' in admin_response.data
    assert b'href="/admin/audit"' in admin_response.data


def test_current_infrastructure_module_is_highlighted(
    client: FlaskClient,
    viewer_user: User,
    sample_asset: Asset,
) -> None:
    login(client, viewer_user, "valid-viewer-password")

    response = client.get("/assets")

    assert response.status_code == 200
    assert b'class="nav-link dropdown-toggle active"' in response.data
    assert b'class="dropdown-item active" href="/assets"' in response.data


def test_error_flash_uses_consistent_visual_alert(
    client: FlaskClient,
    active_user: User,
) -> None:
    response = client.post(
        "/login",
        data={"username": active_user.username, "password": "incorrect-password"},
    )

    assert response.status_code == 200
    assert b'class="alert alert-danger alert-dismissible fade show"' in response.data
    assert b'data-category="danger"' in response.data
    assert b'role="alert"' in response.data
    assert "Erro:".encode() in response.data


def test_custom_stylesheet_is_served(client: FlaskClient) -> None:
    response = client.get("/static/css/app.css")

    assert response.status_code == 200
    assert b"--im-navy" in response.data
