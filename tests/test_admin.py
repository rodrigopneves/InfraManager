from urllib.parse import urlparse

import pytest
from flask import Flask
from flask.testing import FlaskClient
from sqlalchemy.exc import OperationalError

from app.admin.services import (
    AdminOperationError,
    ensure_admin_access_remains,
    update_user,
)
from app.extensions import db
from app.models import User, UserRole
from tests.helpers import complete_login


def login(client: FlaskClient, username: str, password: str) -> None:
    complete_login(client, username, password)


def login_admin(client: FlaskClient) -> None:
    login(client, "admin.demo", "valid-admin-password")


def create_user_data(**overrides) -> dict:
    data = {
        "username": "new.user",
        "email": "new.user@example.com",
        "password": "new-user-password",
        "password_confirmation": "new-user-password",
        "is_active": "y",
        "role": UserRole.VIEWER.value,
    }
    data.update(overrides)
    return data


def test_unauthenticated_user_cannot_access_admin(
    client: FlaskClient,
) -> None:
    response = client.get("/admin/users")

    assert response.status_code == 302
    assert urlparse(response.location).path == "/login"


@pytest.mark.parametrize("role", [UserRole.OPERATOR.value, UserRole.VIEWER.value])
def test_non_admin_user_receives_403(
    role: str,
    client: FlaskClient, active_user: User
) -> None:
    active_user.role = role
    db.session.commit()
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
    assert b"Administrador" in response.data


@pytest.mark.parametrize("role", [UserRole.OPERATOR.value, UserRole.VIEWER.value])
def test_non_admin_roles_can_access_dashboard(
    role: str, client: FlaskClient, active_user: User
) -> None:
    active_user.role = role
    db.session.commit()
    login(client, "login.demo", "valid-test-password")

    response = client.get("/dashboard")

    assert response.status_code == 200
    assert b"Bem-vindo, login.demo." in response.data
    assert "Usuários".encode() not in response.data


@pytest.mark.parametrize("role", [role.value for role in UserRole])
def test_admin_creates_user_with_selected_role(
    role: str, client: FlaskClient, admin_user: User
) -> None:
    login_admin(client)

    response = client.post(
        "/admin/users/new",
        data=create_user_data(
            username="  New.User  ", email="  New.User@Example.COM  ", role=role
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
    assert created_user.role == role


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


def test_invalid_role_from_form_is_rejected(
    client: FlaskClient, admin_user: User
) -> None:
    login_admin(client)

    response = client.post(
        "/admin/users/new", data=create_user_data(role="superadmin")
    )

    assert response.status_code == 200
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
            "role": UserRole.OPERATOR.value,
        },
    )
    db.session.refresh(regular_user)

    assert response.status_code == 302
    assert regular_user.username == "updated.user"
    assert regular_user.email == "updated.user@example.com"
    assert regular_user.is_active is True
    assert regular_user.role == UserRole.OPERATOR.value


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


@pytest.mark.parametrize("role", [UserRole.OPERATOR.value, UserRole.VIEWER.value])
def test_admin_cannot_remove_own_admin_role(
    role: str, client: FlaskClient, admin_user: User
) -> None:
    login_admin(client)

    response = client.post(
        f"/admin/users/{admin_user.id}/edit",
        data={
            "username": admin_user.username,
            "email": admin_user.email,
            "is_active": "y",
            "role": role,
        },
    )
    db.session.refresh(admin_user)

    assert response.status_code == 200
    assert "Você não pode remover seu próprio acesso administrativo.".encode() in (
        response.data
    )
    assert admin_user.role == UserRole.ADMIN.value


@pytest.mark.parametrize(
    ("new_is_active", "new_role"),
    [
        (False, UserRole.ADMIN.value),
        (True, UserRole.OPERATOR.value),
        (True, UserRole.VIEWER.value),
    ],
)
def test_last_active_admin_cannot_be_removed(
    app: Flask, new_is_active: bool, new_role: str
) -> None:
    inactive_actor = User(
        username="inactive.admin",
        email="inactive.admin@example.com",
        is_active=False,
        role=UserRole.ADMIN.value,
    )
    inactive_actor.set_password("inactive-admin-password")
    last_admin = User(
        username="last.admin",
        email="last.admin@example.com",
        role=UserRole.ADMIN.value,
    )
    last_admin.set_password("last-admin-password")
    db.session.add_all([inactive_actor, last_admin])
    db.session.commit()

    with pytest.raises(AdminOperationError, match="último administrador ativo"):
        ensure_admin_access_remains(
            inactive_actor,
            last_admin,
            is_active=new_is_active,
            role=new_role,
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
            "role": UserRole.ADMIN.value,
        },
    )
    db.session.refresh(regular_user)

    assert response.status_code == 403
    assert regular_user.role == UserRole.VIEWER.value


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
    assert user.role == UserRole.ADMIN.value
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


def test_admin_change_rolls_back_when_audit_fails(
    app: Flask,
    admin_user: User,
    regular_user: User,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    original_email = regular_user.email
    original_role = regular_user.role

    def fail_audit(*args, **kwargs):
        raise OperationalError("audit insert", {}, Exception("audit failure"))

    monkeypatch.setattr("app.admin.services.record_event", fail_audit)

    with pytest.raises(OperationalError):
        update_user(
            admin_user,
            regular_user,
            username=regular_user.username,
            email="changed.rollback@example.com",
            is_active=True,
            role=UserRole.OPERATOR.value,
        )

    db.session.refresh(regular_user)
    assert regular_user.email == original_email
    assert regular_user.role == original_role
