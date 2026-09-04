import json
from urllib.parse import urlparse

import pytest
from flask import Flask
from flask.testing import FlaskClient
from sqlalchemy.exc import IntegrityError

from app.datacenter.services import (
    DATACENTERS_PER_PAGE,
    DatacenterCodeConflictError,
    create_datacenter,
    update_datacenter,
)
from app.extensions import db
from app.models import (
    AuditEventType,
    AuditLog,
    Datacenter,
    DatacenterStatus,
    User,
)


def login(client: FlaskClient, username: str, password: str) -> None:
    response = client.post(
        "/login", data={"username": username, "password": password}
    )
    assert response.status_code == 302
    assert urlparse(response.location).path == "/dashboard"


def login_admin(client: FlaskClient) -> None:
    login(client, "admin.demo", "valid-admin-password")


def datacenter_data(**overrides) -> dict[str, str]:
    data = {
        "name": "Datacenter Laboratório",
        "code": "DC-LAB-02",
        "location": "Rio de Janeiro",
        "description": "Ambiente fictício para testes.",
        "status": DatacenterStatus.ACTIVE.value,
    }
    data.update(overrides)
    return data


def get_event(event_type: AuditEventType) -> AuditLog:
    return db.session.scalar(
        db.select(AuditLog).where(AuditLog.event_type == event_type.value)
    )


def test_datacenter_model_normalizes_values_and_sets_defaults(app: Flask) -> None:
    datacenter = Datacenter(
        name="  Datacenter Laboratório  ",
        code="  dc-lab-01  ",
        location="  São Paulo  ",
        description="  Ambiente fictício.  ",
    )
    db.session.add(datacenter)
    db.session.commit()

    assert datacenter.name == "Datacenter Laboratório"
    assert datacenter.code == "DC-LAB-01"
    assert datacenter.location == "São Paulo"
    assert datacenter.description == "Ambiente fictício."
    assert datacenter.status == DatacenterStatus.ACTIVE.value
    assert datacenter.status_label == "Ativo"
    assert datacenter.created_at is not None
    assert datacenter.updated_at is not None


def test_empty_description_is_normalized_to_none(app: Flask) -> None:
    datacenter = Datacenter(
        name="DC sem descrição",
        code="DC-NO-DESCRIPTION",
        location="Curitiba",
        description="   ",
    )

    assert datacenter.description is None


def test_updated_at_changes_when_datacenter_is_updated(app: Flask) -> None:
    datacenter = Datacenter(
        name="DC Original",
        code="DC-TIMESTAMP",
        location="Porto Alegre",
    )
    db.session.add(datacenter)
    db.session.commit()
    original_updated_at = datacenter.updated_at

    datacenter.name = "DC Atualizado"
    db.session.commit()

    assert datacenter.updated_at > original_updated_at


@pytest.mark.parametrize("status", ["active", "inactive"])
def test_datacenter_accepts_supported_statuses(app: Flask, status: str) -> None:
    datacenter = Datacenter(
        name="DC Status",
        code=f"DC-{status}",
        location="Recife",
        status=status,
    )
    db.session.add(datacenter)
    db.session.commit()

    assert datacenter.status == status


def test_datacenter_rejects_invalid_status() -> None:
    with pytest.raises(ValueError, match="status"):
        Datacenter(
            name="DC Inválido",
            code="DC-INVALID",
            location="Brasília",
            status="maintenance",
        )


@pytest.mark.parametrize(
    ("field", "value"),
    [
        ("name", "   "),
        ("code", "   "),
        ("location", "   "),
        ("name", "x" * 121),
        ("code", "x" * 65),
        ("location", "x" * 256),
        ("description", "x" * 1001),
    ],
)
def test_datacenter_model_rejects_empty_or_oversized_fields(
    field: str, value: str
) -> None:
    values = {
        "name": "DC Válido",
        "code": "DC-VALID",
        "location": "São Paulo",
        "description": None,
    }
    values[field] = value

    with pytest.raises(ValueError):
        Datacenter(**values)


def test_required_columns_are_enforced_by_database(app: Flask) -> None:
    datacenter = Datacenter()
    db.session.add(datacenter)

    with pytest.raises(IntegrityError):
        db.session.commit()

    db.session.rollback()


def test_datacenter_code_is_unique_after_normalization(app: Flask) -> None:
    db.session.add(
        Datacenter(name="DC Um", code="DC-LAB-01", location="São Paulo")
    )
    db.session.commit()
    db.session.add(
        Datacenter(name="DC Dois", code=" dc-lab-01 ", location="Curitiba")
    )

    with pytest.raises(IntegrityError):
        db.session.commit()

    db.session.rollback()


def test_code_length_is_validated_after_unicode_uppercase_expansion() -> None:
    code_that_expands_past_limit = "ß" * 33

    with pytest.raises(ValueError, match="length"):
        Datacenter(
            name="DC Unicode",
            code=code_that_expands_past_limit,
            location="São Paulo",
        )


def test_admin_can_create_datacenter(
    client: FlaskClient, admin_user: User
) -> None:
    login_admin(client)

    response = client.post(
        "/datacenters/create",
        data=datacenter_data(
            name="  Novo Datacenter  ",
            code="  dc-new-01  ",
            location="  Fortaleza  ",
            description="  Descrição controlada.  ",
        ),
    )
    created = db.session.scalar(
        db.select(Datacenter).where(Datacenter.code == "DC-NEW-01")
    )

    assert response.status_code == 302
    assert created is not None
    assert urlparse(response.location).path == f"/datacenters/{created.id}"
    assert created.name == "Novo Datacenter"
    assert created.location == "Fortaleza"
    assert created.description == "Descrição controlada."


def test_admin_can_list_and_view_datacenter(
    client: FlaskClient, admin_user: User, sample_datacenter: Datacenter
) -> None:
    login_admin(client)

    list_response = client.get("/datacenters")
    detail_response = client.get(f"/datacenters/{sample_datacenter.id}")

    assert list_response.status_code == 200
    assert sample_datacenter.code.encode() in list_response.data
    assert sample_datacenter.name.encode() in list_response.data
    assert detail_response.status_code == 200
    assert sample_datacenter.description.encode() in detail_response.data


def test_admin_can_update_datacenter(
    client: FlaskClient, admin_user: User, sample_datacenter: Datacenter
) -> None:
    login_admin(client)

    response = client.post(
        f"/datacenters/{sample_datacenter.id}/edit",
        data=datacenter_data(
            name="Datacenter Atualizado",
            code="dc-updated-01",
            status=DatacenterStatus.INACTIVE.value,
        ),
    )
    db.session.refresh(sample_datacenter)

    assert response.status_code == 302
    assert sample_datacenter.name == "Datacenter Atualizado"
    assert sample_datacenter.code == "DC-UPDATED-01"
    assert sample_datacenter.status == DatacenterStatus.INACTIVE.value
    assert sample_datacenter.status_label == "Inativo"


def test_admin_can_delete_datacenter(
    client: FlaskClient, admin_user: User, sample_datacenter: Datacenter
) -> None:
    datacenter_id = sample_datacenter.id
    login_admin(client)

    response = client.post(f"/datacenters/{datacenter_id}/delete")

    assert response.status_code == 302
    assert urlparse(response.location).path == "/datacenters"
    assert db.session.get(Datacenter, datacenter_id) is None


def test_admin_can_open_delete_confirmation_without_changing_data(
    client: FlaskClient, admin_user: User, sample_datacenter: Datacenter
) -> None:
    login_admin(client)

    response = client.get(
        f"/datacenters/{sample_datacenter.id}/delete-confirm"
    )

    assert response.status_code == 200
    assert b"Confirmar exclus" in response.data
    assert sample_datacenter.code.encode() in response.data
    assert sample_datacenter.name.encode() in response.data
    assert db.session.get(Datacenter, sample_datacenter.id) is not None


def test_duplicate_code_is_reported_without_creating_record(
    client: FlaskClient, admin_user: User, sample_datacenter: Datacenter
) -> None:
    login_admin(client)

    response = client.post(
        "/datacenters/create",
        data=datacenter_data(code=" dc-lab-01 "),
    )

    assert response.status_code == 200
    assert "Já existe um Datacenter com este código.".encode() in response.data
    assert (
        db.session.scalar(db.select(db.func.count()).select_from(Datacenter)) == 1
    )


def test_duplicate_code_is_reported_without_updating_record(
    client: FlaskClient, admin_user: User, sample_datacenter: Datacenter
) -> None:
    second_datacenter = Datacenter(
        name="Segundo Datacenter",
        code="DC-LAB-02",
        location="Belo Horizonte",
    )
    db.session.add(second_datacenter)
    db.session.commit()
    login_admin(client)

    response = client.post(
        f"/datacenters/{second_datacenter.id}/edit",
        data=datacenter_data(code="dc-lab-01"),
    )
    db.session.refresh(second_datacenter)

    assert response.status_code == 200
    assert "Já existe um Datacenter com este código.".encode() in response.data
    assert second_datacenter.code == "DC-LAB-02"


@pytest.mark.parametrize(
    ("field", "value", "message"),
    [
        ("name", "   ", "Informe um nome válido."),
        ("code", "   ", "Informe um código válido."),
        ("location", "   ", "Informe uma localização válida."),
        ("description", "x" * 1001, "A descrição é muito longa."),
        ("status", "maintenance", "Not a valid choice."),
    ],
)
def test_create_rejects_invalid_form_values(
    field: str,
    value: str,
    message: str,
    client: FlaskClient,
    admin_user: User,
) -> None:
    login_admin(client)
    data = datacenter_data(**{field: value})

    response = client.post("/datacenters/create", data=data)

    assert response.status_code == 200
    assert message.encode() in response.data
    assert db.session.scalar(db.select(db.func.count()).select_from(Datacenter)) == 0


@pytest.mark.parametrize(
    ("user_fixture", "username", "password"),
    [
        ("admin_user", "admin.demo", "valid-admin-password"),
        ("operator_user", "operator.demo", "valid-operator-password"),
        ("viewer_user", "viewer.demo", "valid-viewer-password"),
    ],
)
def test_all_roles_can_list_and_view_datacenters(
    user_fixture: str,
    username: str,
    password: str,
    request: pytest.FixtureRequest,
    client: FlaskClient,
    sample_datacenter: Datacenter,
) -> None:
    request.getfixturevalue(user_fixture)
    login(client, username, password)

    assert client.get("/datacenters").status_code == 200
    assert client.get(f"/datacenters/{sample_datacenter.id}").status_code == 200


@pytest.mark.parametrize(
    ("user_fixture", "username", "password"),
    [
        ("operator_user", "operator.demo", "valid-operator-password"),
        ("viewer_user", "viewer.demo", "valid-viewer-password"),
    ],
)
@pytest.mark.parametrize(
    ("method", "path_template"),
    [
        ("get", "/datacenters/create"),
        ("post", "/datacenters/create"),
        ("get", "/datacenters/{id}/edit"),
        ("post", "/datacenters/{id}/edit"),
        ("get", "/datacenters/{id}/delete-confirm"),
        ("post", "/datacenters/{id}/delete"),
    ],
)
def test_non_admin_roles_receive_403_for_writes(
    method: str,
    path_template: str,
    user_fixture: str,
    username: str,
    password: str,
    request: pytest.FixtureRequest,
    client: FlaskClient,
    sample_datacenter: Datacenter,
) -> None:
    request.getfixturevalue(user_fixture)
    login(client, username, password)
    path = path_template.format(id=sample_datacenter.id)

    response = getattr(client, method)(path, data=datacenter_data())

    assert response.status_code == 403


@pytest.mark.parametrize(
    "path",
    [
        "/datacenters",
        "/datacenters/1",
        "/datacenters/create",
        "/datacenters/1/edit",
        "/datacenters/1/delete-confirm",
    ],
)
def test_unauthenticated_user_is_redirected_to_login(
    path: str, client: FlaskClient
) -> None:
    response = client.get(path)

    assert response.status_code == 302
    assert urlparse(response.location).path == "/login"


def test_unauthenticated_delete_is_redirected_to_login(client: FlaskClient) -> None:
    response = client.post("/datacenters/1/delete")

    assert response.status_code == 302
    assert urlparse(response.location).path == "/login"


@pytest.mark.parametrize(
    ("method", "path"),
    [
        ("get", "/datacenters/99999"),
        ("get", "/datacenters/99999/edit"),
        ("get", "/datacenters/99999/delete-confirm"),
        ("post", "/datacenters/99999/delete"),
    ],
)
def test_missing_datacenter_returns_404(
    method: str,
    path: str,
    client: FlaskClient,
    admin_user: User,
) -> None:
    login_admin(client)

    assert getattr(client, method)(path).status_code == 404


def test_delete_route_does_not_accept_get(
    client: FlaskClient, admin_user: User, sample_datacenter: Datacenter
) -> None:
    login_admin(client)

    response = client.get(f"/datacenters/{sample_datacenter.id}/delete")

    assert response.status_code == 405
    assert db.session.get(Datacenter, sample_datacenter.id) is not None


def test_non_admin_interface_hides_mutating_actions(
    client: FlaskClient, viewer_user: User, sample_datacenter: Datacenter
) -> None:
    login(client, "viewer.demo", "valid-viewer-password")

    response = client.get("/datacenters")

    assert response.status_code == 200
    assert b"Novo Datacenter" not in response.data
    assert b">Editar<" not in response.data
    assert b">Excluir<" not in response.data


def test_datacenter_list_is_paginated(
    client: FlaskClient, admin_user: User
) -> None:
    db.session.add_all(
        [
            Datacenter(
                name=f"Datacenter {index:02d}",
                code=f"DC-{index:02d}",
                location="Local de teste",
            )
            for index in range(DATACENTERS_PER_PAGE + 1)
        ]
    )
    db.session.commit()
    login_admin(client)

    first_page = client.get("/datacenters")
    second_page = client.get("/datacenters?page=2")

    assert b"DC-00" in first_page.data
    assert b"DC-20" not in first_page.data
    assert "Próxima".encode() in first_page.data
    assert b"DC-20" in second_page.data
    assert "Anterior".encode() in second_page.data


def test_csrf_protects_all_datacenter_writes(
    app: Flask,
    client: FlaskClient,
    admin_user: User,
    sample_datacenter: Datacenter,
) -> None:
    login_admin(client)
    app.config["WTF_CSRF_ENABLED"] = True

    create_response = client.post("/datacenters/create", data=datacenter_data())
    edit_response = client.post(
        f"/datacenters/{sample_datacenter.id}/edit", data=datacenter_data()
    )
    delete_response = client.post(
        f"/datacenters/{sample_datacenter.id}/delete"
    )

    assert create_response.status_code == 400
    assert edit_response.status_code == 400
    assert delete_response.status_code == 400
    assert db.session.get(Datacenter, sample_datacenter.id) is not None


def test_user_content_is_escaped_in_detail_template(
    client: FlaskClient, admin_user: User
) -> None:
    datacenter = Datacenter(
        name="<script>alert('name')</script>",
        code="DC-XSS-01",
        location="<b>Local</b>",
        description="<img src=x onerror=alert('description')>",
    )
    db.session.add(datacenter)
    db.session.commit()
    login_admin(client)

    response = client.get(f"/datacenters/{datacenter.id}")

    assert response.status_code == 200
    assert b"<script>" not in response.data
    assert b"<img src=x" not in response.data
    assert b"&lt;script&gt;" in response.data
    assert b"&lt;img src=x" in response.data


def test_create_update_and_delete_are_audited_without_submitted_values(
    client: FlaskClient, admin_user: User
) -> None:
    login_admin(client)
    sensitive_description = "token=must-not-be-audited"
    create_response = client.post(
        "/datacenters/create",
        data=datacenter_data(description=sensitive_description),
    )
    datacenter = db.session.scalar(
        db.select(Datacenter).where(Datacenter.code == "DC-LAB-02")
    )
    assert create_response.status_code == 302

    client.post(
        f"/datacenters/{datacenter.id}/edit",
        data=datacenter_data(name="Nome alterado", description="novo segredo"),
    )
    client.post(f"/datacenters/{datacenter.id}/delete")

    events = {
        event_type: get_event(event_type)
        for event_type in (
            AuditEventType.DATACENTER_CREATE,
            AuditEventType.DATACENTER_UPDATE,
            AuditEventType.DATACENTER_DELETE,
        )
    }
    for audit_log in events.values():
        assert audit_log.actor_user_id == admin_user.id
        assert audit_log.resource_type == "datacenter"
        assert audit_log.resource_id == datacenter.id
        assert audit_log.result == "success"

    assert events[AuditEventType.DATACENTER_CREATE].details == {}
    assert events[AuditEventType.DATACENTER_UPDATE].details == {
        "changed_fields": ["description", "name"]
    }
    assert events[AuditEventType.DATACENTER_DELETE].details == {}
    serialized_details = json.dumps(
        [audit_log.details for audit_log in events.values()]
    )
    assert sensitive_description not in serialized_details
    assert "novo segredo" not in serialized_details


@pytest.mark.parametrize("operation", ["create", "update"])
def test_audit_integrity_error_is_not_reported_as_code_conflict(
    operation: str,
    monkeypatch: pytest.MonkeyPatch,
    admin_user: User,
    sample_datacenter: Datacenter,
) -> None:
    def fail_audit(*args, **kwargs):
        raise IntegrityError(
            "audit insert", {}, Exception("audit integrity failure")
        )

    monkeypatch.setattr("app.datacenter.services.record_event", fail_audit)

    if operation == "create":
        with pytest.raises(IntegrityError) as error:
            create_datacenter(
                admin_user,
                name="Datacenter com falha de auditoria",
                code="DC-AUDIT-FAIL",
                location="São Paulo",
                description=None,
                status=DatacenterStatus.ACTIVE.value,
            )
        assert db.session.scalar(
            db.select(Datacenter).where(Datacenter.code == "DC-AUDIT-FAIL")
        ) is None
    else:
        original_name = sample_datacenter.name
        with pytest.raises(IntegrityError) as error:
            update_datacenter(
                admin_user,
                sample_datacenter,
                name="Nome que deve sofrer rollback",
                code=sample_datacenter.code,
                location=sample_datacenter.location,
                description=sample_datacenter.description,
                status=sample_datacenter.status,
            )
        db.session.refresh(sample_datacenter)
        assert sample_datacenter.name == original_name

    assert not isinstance(error.value, DatacenterCodeConflictError)
