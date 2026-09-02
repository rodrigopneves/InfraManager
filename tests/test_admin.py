from urllib.parse import urlparse

import pytest
from flask import Flask
from flask.testing import FlaskClient
from app.admin.services import AdminOperationError, ensure_admin_access_remains
from app.extensions import db
from app.models import User


def login(client: FlaskClient, username: str, password: str) -> None:
    response = client.post(
        "/login", data={"username": username, "password": password}
    )
    assert response.status_code == 302


def login_admin(client: FlaskClient) -> None:
    login(client, "admin.demo", "valid-admin-password")


def create_user_data(**overrides) -> dict:
    data = {
        "username": "new.user",
        "email": "new.user@example.com",
        "password": "new-user-password",
        "password_confirmation": "new-user-password",
        "is_active": "y",
    }
    data.update(overrides)
    return data


def test_unauthenticated_user_cannot_access_admin(
    client: FlaskClient,
) -> None:
    response = client.get("/admin/users")

    assert response.status_code == 302
    assert urlparse(response.location).path == "/login"


def test_non_admin_user_receives_403(
    client: FlaskClient, active_user: User
) -> None:
    login(client, "login.demo", "valid-test-password")

    response = client.get("/admin/users")

    assert response.status_code == 403
    assert "Você não possui permissão".encode() in response.data


def test_admin_can_list_users(client: FlaskClient, admin_user: User) -> None:
    login_admin(client)

    response = client.get("/admin/users")

    assert response.status_code == 200
    assert b"admin.demo" in response.data
    assert b"admin.demo@example.com" in response.data


def test_admin_creates_normalized_user_with_hashed_password(
    client: FlaskClient, admin_user: User
) -> None:
    login_admin(client)

    response = client.post(
        "/admin/users/new",
        data=create_user_data(
            username="  New.User  ", email="  New.User@Example.COM  "
        ),
    )
    created_user = db.session.scalar(
        db.select(User).where(User.username == "new.user")
    )

    assert response.status_code == 302
    assert created_user is not None
    assert created_user.email == "new.user@example.com"
    assert created_user.password_hash != "new-user-password"
    assert created_user.check_password("new-user-password") is True
    assert created_user.is_active is True
    assert created_user.is_admin is False


def test_duplicate_username_is_rejected(
    client: FlaskClient, admin_user: User
) -> None:
    login_admin(client)

    response = client.post(
        "/admin/users/new",
        data=create_user_data(
            username="ADMIN.DEMO", email="another.user@example.com"
        ),
    )

    assert response.status_code == 200
    assert "Este nome de usuário já está em uso.".encode() in response.data
    assert db.session.scalar(db.select(db.func.count()).select_from(User)) == 1


def test_duplicate_email_is_rejected(
    client: FlaskClient, admin_user: User
) -> None:
    login_admin(client)

    response = client.post(
        "/admin/users/new",
        data=create_user_data(
            username="another.user", email="ADMIN.DEMO@EXAMPLE.COM"
        ),
    )

    assert response.status_code == 200
    assert "Este e-mail já está em uso.".encode() in response.data
    assert db.session.scalar(db.select(db.func.count()).select_from(User)) == 1


def test_admin_edits_user(
    client: FlaskClient, admin_user: User, regular_user: User
) -> None:
    login_admin(client)

    response = client.post(
        f"/admin/users/{regular_user.id}/edit",
        data={
            "username": "  Updated.User ",
            "email": " Updated.User@Example.COM ",
            "is_active": "y",
        },
    )
    db.session.refresh(regular_user)

    assert response.status_code == 302
    assert regular_user.username == "updated.user"
    assert regular_user.email == "updated.user@example.com"
    assert regular_user.is_active is True
    assert regular_user.is_admin is False


def test_admin_can_deactivate_and_reactivate_user(
    client: FlaskClient, admin_user: User, regular_user: User
) -> None:
    login_admin(client)
    url = f"/admin/users/{regular_user.id}/toggle-active"

    first_response = client.post(url)
    db.session.refresh(regular_user)
    assert first_response.status_code == 302
    assert regular_user.is_active is False

    second_response = client.post(url)
    db.session.refresh(regular_user)
    assert second_response.status_code == 302
    assert regular_user.is_active is True


def test_toggle_active_requires_post_and_csrf(
    app: Flask, client: FlaskClient, admin_user: User, regular_user: User
) -> None:
    login_admin(client)
    url = f"/admin/users/{regular_user.id}/toggle-active"

    assert client.get(url).status_code == 405
    app.config["WTF_CSRF_ENABLED"] = True
    assert client.post(url).status_code == 400


def test_admin_cannot_deactivate_own_account(
    client: FlaskClient, admin_user: User
) -> None:
    login_admin(client)

    response = client.post(
        f"/admin/users/{admin_user.id}/toggle-active", follow_redirects=True
    )
    db.session.refresh(admin_user)

    assert response.status_code == 200
    assert "Você não pode desativar sua própria conta.".encode() in response.data
    assert admin_user.is_active is True


def test_admin_cannot_remove_own_admin_status(
    client: FlaskClient, admin_user: User
) -> None:
    login_admin(client)

    response = client.post(
        f"/admin/users/{admin_user.id}/edit",
        data={
            "username": admin_user.username,
            "email": admin_user.email,
            "is_active": "y",
        },
    )
    db.session.refresh(admin_user)

    assert response.status_code == 200
    assert "Você não pode remover seu próprio acesso administrativo.".encode() in (
        response.data
    )
    assert admin_user.is_admin is True


def test_last_active_admin_cannot_be_removed(app: Flask) -> None:
    inactive_actor = User(
        username="inactive.admin",
        email="inactive.admin@example.com",
        is_active=False,
        is_admin=True,
    )
    inactive_actor.set_password("inactive-admin-password")
    last_admin = User(
        username="last.admin",
        email="last.admin@example.com",
        is_admin=True,
    )
    last_admin.set_password("last-admin-password")
    db.session.add_all([inactive_actor, last_admin])
    db.session.commit()

    with pytest.raises(AdminOperationError, match="último administrador ativo"):
        ensure_admin_access_remains(
            inactive_actor,
            last_admin,
            is_active=False,
            is_admin=last_admin.is_admin,
        )


def test_non_admin_cannot_promote_self_directly(
    client: FlaskClient, regular_user: User
) -> None:
    login(client, "user.demo", "valid-user-password")

    response = client.post(
        f"/admin/users/{regular_user.id}/edit",
        data={
            "username": regular_user.username,
            "email": regular_user.email,
            "is_active": "y",
            "is_admin": "y",
        },
    )
    db.session.refresh(regular_user)

    assert response.status_code == 403
    assert regular_user.is_admin is False


def test_create_admin_command_creates_admin(app: Flask) -> None:
    runner = app.test_cli_runner()

    result = runner.invoke(
        args=["create-admin"],
        input=(
            "  CLI.Admin  \n"
            "  CLI.Admin@Example.COM  \n"
            "cli-admin-password\n"
            "cli-admin-password\n"
        ),
    )
    user = db.session.scalar(
        db.select(User).where(User.username == "cli.admin")
    )

    assert result.exit_code == 0
    assert user is not None
    assert user.email == "cli.admin@example.com"
    assert user.is_admin is True
    assert user.is_active is True
    assert user.check_password("cli-admin-password") is True
    assert "cli-admin-password" not in result.output


def test_create_admin_command_rejects_duplicate(app: Flask, admin_user: User) -> None:
    runner = app.test_cli_runner()

    result = runner.invoke(
        args=["create-admin"],
        input="ADMIN.DEMO\nanother.email@example.com\n",
    )

    assert result.exit_code != 0
    assert "Username já cadastrado." in result.output
    assert db.session.scalar(db.select(db.func.count()).select_from(User)) == 1
