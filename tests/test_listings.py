import pytest
from flask.testing import FlaskClient

from app.models import User, VirtualMachine
from tests.helpers import complete_login


def login(client: FlaskClient, user: User, password: str) -> None:
    complete_login(client, user.username, password)


@pytest.mark.parametrize(
    ("path", "empty_message", "create_path"),
    [
        ("/datacenters", "Nenhum Datacenter cadastrado.", "/datacenters/create"),
        ("/rooms", "Nenhuma Sala cadastrada.", "/rooms/create"),
        ("/racks", "Nenhum Rack cadastrado.", "/racks/create"),
        ("/assets", "Nenhum Ativo cadastrado.", "/assets/create"),
        (
            "/virtual-machines",
            "Nenhuma Máquina Virtual cadastrada.",
            "/virtual-machines/create",
        ),
    ],
)
def test_empty_lists_offer_creation_only_to_admin(
    path: str,
    empty_message: str,
    create_path: str,
    client: FlaskClient,
    admin_user: User,
) -> None:
    login(client, admin_user, "valid-admin-password")

    response = client.get(path)

    assert response.status_code == 200
    assert empty_message.encode() in response.data
    assert f'href="{create_path}"'.encode() in response.data
    assert b"<table" not in response.data


@pytest.mark.parametrize(
    ("path", "empty_message", "create_path"),
    [
        ("/datacenters", "Nenhum Datacenter cadastrado.", "/datacenters/create"),
        ("/rooms", "Nenhuma Sala cadastrada.", "/rooms/create"),
        ("/racks", "Nenhum Rack cadastrado.", "/racks/create"),
        ("/assets", "Nenhum Ativo cadastrado.", "/assets/create"),
        (
            "/virtual-machines",
            "Nenhuma Máquina Virtual cadastrada.",
            "/virtual-machines/create",
        ),
    ],
)
def test_empty_lists_do_not_offer_unauthorized_creation(
    path: str,
    empty_message: str,
    create_path: str,
    client: FlaskClient,
    viewer_user: User,
) -> None:
    login(client, viewer_user, "valid-viewer-password")

    response = client.get(path)

    assert response.status_code == 200
    assert empty_message.encode() in response.data
    assert f'href="{create_path}"'.encode() not in response.data


@pytest.mark.parametrize(
    ("path", "record_text", "status_text"),
    [
        ("/datacenters", "DC-LAB-01", "Ativo"),
        ("/rooms", "ROOM-LAB-01", "Ativo"),
        ("/racks", "RACK-LAB-01", "Ativo"),
        ("/assets", "SRV-LAB-01", "Ativo"),
        ("/virtual-machines", "VM-LAB-01", "Desligada"),
    ],
)
def test_populated_infrastructure_lists_show_records_and_statuses(
    path: str,
    record_text: str,
    status_text: str,
    client: FlaskClient,
    viewer_user: User,
    sample_virtual_machine: VirtualMachine,
) -> None:
    login(client, viewer_user, "valid-viewer-password")

    response = client.get(path)

    assert response.status_code == 200
    assert record_text.encode() in response.data
    assert status_text.encode() in response.data
    assert b"<table" in response.data
    assert b">Detalhes<" in response.data
    assert b">Editar<" not in response.data
    assert b">Excluir<" not in response.data


def test_user_activation_remains_a_csrf_protected_post_action(
    client: FlaskClient,
    admin_user: User,
) -> None:
    login(client, admin_user, "valid-admin-password")

    response = client.get("/admin/users")

    assert response.status_code == 200
    assert b'method="post"' in response.data
    assert f'action="/admin/users/{admin_user.id}/toggle-active"'.encode() in response.data
    assert b'name="csrf_token"' in response.data
