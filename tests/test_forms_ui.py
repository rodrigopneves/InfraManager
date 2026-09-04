from flask.testing import FlaskClient

from app.models import Datacenter, Room, User


def login(client: FlaskClient, user: User, password: str) -> None:
    response = client.post(
        "/login",
        data={"username": user.username, "password": password},
    )
    assert response.status_code == 302


def test_login_displays_required_errors_in_portuguese(client: FlaskClient) -> None:
    response = client.post("/login", data={"username": "", "password": ""})

    assert response.status_code == 200
    assert "Informe seu usuário.".encode() in response.data
    assert "Informe sua senha.".encode() in response.data
    assert response.data.count(b'aria-invalid="true"') >= 2
    assert b'aria-describedby="username-errors"' in response.data
    assert b'aria-describedby="password-errors"' in response.data


def test_mfa_invalid_field_has_accessible_feedback(
    client: FlaskClient,
    mfa_user: User,
) -> None:
    client.post(
        "/login",
        data={"username": mfa_user.username, "password": "valid-mfa-password"},
    )

    response = client.post("/mfa/verify", data={"code": "12ab56"})

    assert response.status_code == 200
    assert "Código inválido.".encode() in response.data
    assert b'aria-invalid="true"' in response.data
    assert b'aria-describedby="code-help code-errors"' in response.data
    assert b"12ab56" not in response.data


def test_user_form_preserves_password_field_types_and_guidance(
    client: FlaskClient,
    admin_user: User,
) -> None:
    login(client, admin_user, "valid-admin-password")

    response = client.get("/admin/users/new")

    assert response.status_code == 200
    assert b'type="password"' in response.data
    assert response.data.count(b'autocomplete="new-password"') == 2
    assert "Utilize no mínimo 8 caracteres.".encode() in response.data
    assert "Obrigatório".encode() in response.data
    assert b'aria-describedby="None"' not in response.data


def test_infrastructure_form_keeps_invalid_value_and_field_error(
    client: FlaskClient,
    admin_user: User,
) -> None:
    login(client, admin_user, "valid-admin-password")

    response = client.post(
        "/datacenters/create",
        data={
            "name": "Datacenter Teste",
            "code": "",
            "location": "São Paulo",
            "description": "",
            "status": "active",
        },
    )

    assert response.status_code == 200
    assert b'value="Datacenter Teste"' in response.data
    assert "Informe um código válido.".encode() in response.data
    assert b'aria-invalid="true"' in response.data
    assert b'aria-describedby="code-help code-errors"' in response.data


def test_relationship_select_explains_required_parent(
    client: FlaskClient,
    admin_user: User,
    sample_datacenter: Datacenter,
) -> None:
    login(client, admin_user, "valid-admin-password")

    response = client.get("/rooms/create")

    assert response.status_code == 200
    assert b'name="datacenter_id"' in response.data
    assert sample_datacenter.code.encode() in response.data
    assert "Toda Sala deve pertencer a um Datacenter.".encode() in response.data
    assert "Obrigatório".encode() in response.data


def test_delete_confirmation_keeps_post_and_csrf(
    client: FlaskClient,
    admin_user: User,
    sample_datacenter: Datacenter,
) -> None:
    login(client, admin_user, "valid-admin-password")

    response = client.get(f"/datacenters/{sample_datacenter.id}/delete-confirm")

    assert response.status_code == 200
    assert b'method="post"' in response.data
    assert (
        f'action="/datacenters/{sample_datacenter.id}/delete"'.encode()
        in response.data
    )
    assert b'name="csrf_token"' in response.data
    assert "Esta ação não poderá ser desfeita.".encode() in response.data
    assert "Confirmar exclusão</button>".encode() in response.data


def test_blocked_delete_confirmation_has_no_destructive_action(
    client: FlaskClient,
    admin_user: User,
    sample_room: Room,
) -> None:
    login(client, admin_user, "valid-admin-password")

    response = client.get(
        f"/datacenters/{sample_room.datacenter_id}/delete-confirm"
    )

    assert response.status_code == 200
    assert "não pode ser excluído enquanto possuir Salas".encode() in response.data
    assert "Confirmar exclusão</button>".encode() not in response.data
