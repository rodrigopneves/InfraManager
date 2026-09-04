import pytest
from flask import Flask, abort
from flask.testing import FlaskClient

from app.models import Datacenter, Room, User


def login(client: FlaskClient, user: User, password: str) -> None:
    response = client.post(
        "/login",
        data={"username": user.username, "password": password},
    )
    assert response.status_code == 302


def test_crud_success_uses_accessible_success_feedback(
    client: FlaskClient, admin_user: User
) -> None:
    login(client, admin_user, "valid-admin-password")

    response = client.post(
        "/datacenters/create",
        data={
            "name": "Datacenter de Feedback",
            "code": "DC-FEEDBACK-01",
            "location": "São Paulo",
            "description": "Ambiente fictício.",
            "status": "active",
        },
        follow_redirects=True,
    )

    assert response.status_code == 200
    assert b'class="alert alert-success alert-dismissible fade show"' in response.data
    assert b'data-category="success"' in response.data
    assert b'role="status"' in response.data
    assert "Sucesso:".encode() in response.data
    assert "Datacenter criado com sucesso.".encode() in response.data


def test_dependency_block_uses_accessible_warning_feedback(
    client: FlaskClient,
    admin_user: User,
    sample_datacenter: Datacenter,
    sample_room: Room,
) -> None:
    login(client, admin_user, "valid-admin-password")

    response = client.post(
        f"/datacenters/{sample_datacenter.id}/delete",
        follow_redirects=True,
    )

    assert response.status_code == 200
    assert b'class="alert alert-warning alert-dismissible fade show"' in response.data
    assert b'data-category="warning"' in response.data
    assert b'role="alert"' in response.data
    assert "Atenção:".encode() in response.data
    assert "não pode ser excluído enquanto possuir Salas".encode() in response.data


def test_403_page_is_custom_and_keeps_authorization_behavior(
    client: FlaskClient, viewer_user: User
) -> None:
    login(client, viewer_user, "valid-viewer-password")

    response = client.get("/admin/users")

    assert response.status_code == 403
    assert "Acesso negado".encode() in response.data
    assert "Você não possui permissão".encode() in response.data
    assert b'href="/dashboard"' in response.data
    assert b"admin_required" not in response.data


def test_404_page_is_custom_and_does_not_reveal_requested_route(
    client: FlaskClient,
) -> None:
    sensitive_path = "/internal/secret-resource-name"

    response = client.get(sensitive_path)

    assert response.status_code == 404
    assert "Página não encontrada".encode() in response.data
    assert b'href="/"' in response.data
    assert sensitive_path.encode() not in response.data


def test_generic_400_page_is_custom_and_safe(
    app: Flask, client: FlaskClient
) -> None:
    @app.get("/_test/bad-request")
    def bad_request_for_test():
        abort(400, description="query=SELECT secret FROM users")

    response = client.get("/_test/bad-request")

    assert response.status_code == 400
    assert "Solicitação inválida".encode() in response.data
    assert b"SELECT secret" not in response.data
    assert b"query=" not in response.data


def test_500_page_is_custom_and_does_not_expose_exception(
    app: Flask, client: FlaskClient
) -> None:
    app.config["PROPAGATE_EXCEPTIONS"] = False

    @app.get("/_test/internal-error")
    def internal_error_for_test():
        raise RuntimeError("sensitive/internal/path database query")

    response = client.get("/_test/internal-error")

    assert response.status_code == 500
    assert "Não foi possível concluir a operação".encode() in response.data
    assert "Ocorreu um erro interno.".encode() in response.data
    assert b"RuntimeError" not in response.data
    assert b"sensitive/internal/path" not in response.data
    assert b"database query" not in response.data


def test_exception_propagation_remains_available_for_debugging(
    app: Flask, client: FlaskClient
) -> None:
    app.config["PROPAGATE_EXCEPTIONS"] = True

    @app.get("/_test/debug-error")
    def debug_error_for_test():
        raise RuntimeError("debugging remains available")

    with pytest.raises(RuntimeError, match="debugging remains available"):
        client.get("/_test/debug-error")
