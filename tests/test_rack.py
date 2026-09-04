import json
from urllib.parse import urlparse

import pytest
from flask import Flask
from flask.testing import FlaskClient
from sqlalchemy.exc import IntegrityError

from app.extensions import db
from app.models import (
    AuditEventType,
    AuditLog,
    Datacenter,
    Rack,
    RackStatus,
    Room,
    User,
)
from app.rack.services import (
    RACKS_PER_PAGE,
    RackCodeConflictError,
    create_rack,
    delete_rack,
    update_rack,
)
from app.room.services import RoomHasRacksError, delete_room
from tests.helpers import complete_login


def login(client: FlaskClient, username: str, password: str) -> None:
    complete_login(client, username, password)


def login_admin(client: FlaskClient) -> None:
    login(client, "admin.demo", "valid-admin-password")


def rack_data(parent_room_id: int, **overrides) -> dict[str, str | int]:
    data: dict[str, str | int] = {
        "room_id": parent_room_id,
        "name": "Rack de Laboratório",
        "code": "RACK-LAB-02",
        "capacity_u": 42,
        "description": "Ambiente fictício para testes.",
        "status": RackStatus.ACTIVE.value,
    }
    data.update(overrides)
    return data


def test_rack_model_normalizes_values_and_builds_hierarchy(
    app: Flask, sample_room: Room, sample_datacenter: Datacenter
) -> None:
    rack = Rack(
        room_id=sample_room.id,
        name="  Rack Principal  ",
        code="  rack-01  ",
        capacity_u=48,
        description="  Descrição fictícia.  ",
    )
    db.session.add(rack)
    db.session.commit()
    assert rack.name == "Rack Principal"
    assert rack.code == "RACK-01"
    assert rack.capacity_u == 48
    assert rack.description == "Descrição fictícia."
    assert rack.status == RackStatus.ACTIVE.value
    assert rack.status_label == "Ativo"
    assert rack.created_at is not None
    assert rack.updated_at is not None
    assert rack.room == sample_room
    assert rack.room.datacenter == sample_datacenter
    assert rack in sample_room.racks


def test_rack_updated_at_and_empty_description(
    app: Flask, sample_room: Room
) -> None:
    rack = Rack(
        room_id=sample_room.id,
        name="Rack Original",
        code="RACK-TIMESTAMP",
        capacity_u=1,
        description="   ",
    )
    db.session.add(rack)
    db.session.commit()
    original = rack.updated_at
    assert rack.description is None
    rack.name = "Rack Atualizado"
    db.session.commit()
    assert rack.updated_at > original


@pytest.mark.parametrize("status", ["active", "inactive"])
def test_rack_accepts_supported_statuses(status: str, sample_room: Room) -> None:
    rack = Rack(
        room_id=sample_room.id,
        name="Rack Status",
        code=f"RACK-{status}",
        capacity_u=100,
        status=status,
    )
    db.session.add(rack)
    db.session.commit()
    assert rack.status == status


@pytest.mark.parametrize(
    ("field", "value"),
    [
        ("room_id", 0),
        ("name", "   "),
        ("name", "x" * 121),
        ("code", "   "),
        ("code", "x" * 65),
        ("capacity_u", 0),
        ("capacity_u", -1),
        ("capacity_u", 101),
        ("capacity_u", True),
        ("description", "x" * 1001),
        ("status", "maintenance"),
    ],
)
def test_rack_model_rejects_invalid_values(
    field: str, value: str | int | bool, sample_room: Room
) -> None:
    values = {
        "room_id": sample_room.id,
        "name": "Rack válido",
        "code": "RACK-VALID",
        "capacity_u": 42,
        "description": None,
        "status": RackStatus.ACTIVE.value,
    }
    values[field] = value
    with pytest.raises(ValueError):
        Rack(**values)


def test_rack_code_length_is_checked_after_unicode_expansion(
    sample_room: Room,
) -> None:
    with pytest.raises(ValueError, match="length"):
        Rack(
            room_id=sample_room.id,
            name="Rack Unicode",
            code="ß" * 33,
            capacity_u=42,
        )


def test_database_enforces_required_columns(app: Flask) -> None:
    db.session.add(Rack())
    with pytest.raises(IntegrityError):
        db.session.commit()
    db.session.rollback()


def test_foreign_key_and_capacity_check_are_enforced(
    app: Flask, sample_room: Room
) -> None:
    assert db.session.scalar(db.text("PRAGMA foreign_keys")) == 1
    with pytest.raises(IntegrityError):
        db.session.execute(
            db.insert(Rack.__table__).values(
                room_id=99999,
                name="Rack órfão",
                code="RACK-ORPHAN",
                capacity_u=42,
            )
        )
    db.session.rollback()
    with pytest.raises(IntegrityError):
        db.session.execute(
            db.insert(Rack.__table__).values(
                room_id=sample_room.id,
                name="Rack inválido",
                code="RACK-ZERO",
                capacity_u=0,
            )
        )
    db.session.rollback()


def test_rack_code_is_unique_only_inside_same_room(
    app: Flask, sample_datacenter: Datacenter, sample_room: Room
) -> None:
    other_room = Room(
        datacenter_id=sample_datacenter.id, name="Sala Dois", code="ROOM-02"
    )
    db.session.add(other_room)
    db.session.flush()
    db.session.add_all(
        [
            Rack(room_id=sample_room.id, name="Rack Um", code="RACK-01", capacity_u=42),
            Rack(room_id=other_room.id, name="Rack Dois", code="rack-01", capacity_u=42),
        ]
    )
    db.session.commit()
    db.session.add(
        Rack(
            room_id=sample_room.id,
            name="Rack Duplicado",
            code=" rack-01 ",
            capacity_u=42,
        )
    )
    with pytest.raises(IntegrityError):
        db.session.commit()
    db.session.rollback()


def test_admin_can_create_read_update_and_delete_rack(
    client: FlaskClient, admin_user: User, sample_room: Room
) -> None:
    login_admin(client)
    created_response = client.post(
        "/racks/create",
        data=rack_data(
            sample_room.id,
            name="  Rack Novo  ",
            code="  rack-new-01  ",
            capacity_u=48,
            description="  Texto controlado.  ",
        ),
    )
    rack = db.session.scalar(db.select(Rack).where(Rack.code == "RACK-NEW-01"))
    assert created_response.status_code == 302
    assert rack is not None
    assert rack.name == "Rack Novo"
    assert rack.description == "Texto controlado."
    assert client.get("/racks").status_code == 200
    detail = client.get(f"/racks/{rack.id}")
    assert detail.status_code == 200
    assert b"48 U" in detail.data

    updated = client.post(
        f"/racks/{rack.id}/edit",
        data=rack_data(
            sample_room.id,
            name="Rack Atualizado",
            code="RACK-UPDATED",
            capacity_u=24,
            status=RackStatus.INACTIVE.value,
        ),
    )
    db.session.refresh(rack)
    assert updated.status_code == 302
    assert rack.name == "Rack Atualizado"
    assert rack.code == "RACK-UPDATED"
    assert rack.capacity_u == 24
    assert rack.status_label == "Inativo"

    confirmation = client.get(f"/racks/{rack.id}/delete-confirm")
    assert confirmation.status_code == 200
    assert db.session.get(Rack, rack.id) is not None
    deleted = client.post(f"/racks/{rack.id}/delete")
    assert deleted.status_code == 302
    assert db.session.get(Rack, rack.id) is None


def test_create_query_preselects_only_existing_room(
    client: FlaskClient, admin_user: User, sample_room: Room
) -> None:
    login_admin(client)
    valid = client.get(f"/racks/create?room_id={sample_room.id}")
    invalid = client.get("/racks/create?room_id=99999")
    assert f'selected value="{sample_room.id}"'.encode() in valid.data
    assert sample_room.datacenter.code.encode() in valid.data
    assert b'value="99999"' not in invalid.data


def test_rack_move_and_destination_conflict(
    client: FlaskClient,
    admin_user: User,
    sample_datacenter: Datacenter,
    sample_rack: Rack,
) -> None:
    destination = Room(
        datacenter_id=sample_datacenter.id, name="Sala Destino", code="ROOM-DEST"
    )
    db.session.add(destination)
    db.session.flush()
    db.session.add(
        Rack(room_id=destination.id, name="Ocupado", code="USED", capacity_u=42)
    )
    db.session.commit()
    login_admin(client)
    moved = client.post(
        f"/racks/{sample_rack.id}/edit",
        data=rack_data(destination.id, code="FREE"),
    )
    assert moved.status_code == 302
    db.session.refresh(sample_rack)
    assert sample_rack.room_id == destination.id
    conflict = client.post(
        f"/racks/{sample_rack.id}/edit",
        data=rack_data(destination.id, code=" used "),
    )
    db.session.refresh(sample_rack)
    assert conflict.status_code == 200
    assert "Já existe um Rack".encode() in conflict.data
    assert sample_rack.code == "FREE"


@pytest.mark.parametrize(
    ("field", "value", "message"),
    [
        ("room_id", 99999, "Not a valid choice."),
        ("name", "   ", "Informe um nome válido."),
        ("code", "   ", "Informe um código válido."),
        ("capacity_u", "texto", "Not a valid integer value."),
        ("capacity_u", 0, "A capacidade deve estar entre 1 e 100 U."),
        ("capacity_u", 101, "A capacidade deve estar entre 1 e 100 U."),
        ("description", "x" * 1001, "A descrição é muito longa."),
        ("status", "maintenance", "Not a valid choice."),
    ],
)
def test_create_rejects_invalid_form_values(
    field: str,
    value: str | int,
    message: str,
    client: FlaskClient,
    admin_user: User,
    sample_room: Room,
) -> None:
    login_admin(client)
    response = client.post(
        "/racks/create", data=rack_data(sample_room.id, **{field: value})
    )
    assert response.status_code == 200
    assert message.encode() in response.data
    assert db.session.scalar(db.select(db.func.count()).select_from(Rack)) == 0


@pytest.mark.parametrize(
    ("fixture_name", "username", "password"),
    [
        ("admin_user", "admin.demo", "valid-admin-password"),
        ("operator_user", "operator.demo", "valid-operator-password"),
        ("viewer_user", "viewer.demo", "valid-viewer-password"),
    ],
)
def test_all_roles_can_list_and_view_racks(
    fixture_name: str,
    username: str,
    password: str,
    request: pytest.FixtureRequest,
    client: FlaskClient,
    sample_rack: Rack,
) -> None:
    request.getfixturevalue(fixture_name)
    login(client, username, password)
    assert client.get("/racks").status_code == 200
    assert client.get(f"/racks/{sample_rack.id}").status_code == 200


@pytest.mark.parametrize(
    ("fixture_name", "username", "password"),
    [
        ("operator_user", "operator.demo", "valid-operator-password"),
        ("viewer_user", "viewer.demo", "valid-viewer-password"),
    ],
)
@pytest.mark.parametrize(
    ("method", "path_template"),
    [
        ("get", "/racks/create"),
        ("post", "/racks/create"),
        ("get", "/racks/{id}/edit"),
        ("post", "/racks/{id}/edit"),
        ("get", "/racks/{id}/delete-confirm"),
        ("post", "/racks/{id}/delete"),
    ],
)
def test_non_admin_roles_receive_403_for_rack_writes(
    fixture_name: str,
    username: str,
    password: str,
    method: str,
    path_template: str,
    request: pytest.FixtureRequest,
    client: FlaskClient,
    sample_rack: Rack,
) -> None:
    request.getfixturevalue(fixture_name)
    login(client, username, password)
    response = getattr(client, method)(
        path_template.format(id=sample_rack.id), data=rack_data(sample_rack.room_id)
    )
    assert response.status_code == 403


@pytest.mark.parametrize(
    ("method", "path"),
    [
        ("get", "/racks"),
        ("get", "/racks/1"),
        ("get", "/racks/create"),
        ("get", "/racks/1/edit"),
        ("get", "/racks/1/delete-confirm"),
        ("post", "/racks/1/delete"),
    ],
)
def test_unauthenticated_routes_redirect_to_login(
    method: str, path: str, client: FlaskClient
) -> None:
    response = getattr(client, method)(path)
    assert response.status_code == 302
    assert urlparse(response.location).path == "/login"


@pytest.mark.parametrize(
    ("method", "path"),
    [
        ("get", "/racks/99999"),
        ("get", "/racks/99999/edit"),
        ("get", "/racks/99999/delete-confirm"),
        ("post", "/racks/99999/delete"),
    ],
)
def test_missing_rack_returns_404(
    method: str, path: str, client: FlaskClient, admin_user: User
) -> None:
    login_admin(client)
    assert getattr(client, method)(path).status_code == 404


def test_delete_rejects_get_and_writes_require_csrf(
    app: Flask, client: FlaskClient, admin_user: User, sample_rack: Rack
) -> None:
    login_admin(client)
    assert client.get(f"/racks/{sample_rack.id}/delete").status_code == 405
    app.config["WTF_CSRF_ENABLED"] = True
    assert client.post("/racks/create", data={}).status_code == 400
    assert client.post(f"/racks/{sample_rack.id}/edit", data={}).status_code == 400
    assert client.post(f"/racks/{sample_rack.id}/delete").status_code == 400
    assert db.session.get(Rack, sample_rack.id) is not None


def test_viewer_interface_hides_mutating_actions(
    client: FlaskClient, viewer_user: User, sample_rack: Rack
) -> None:
    login(client, "viewer.demo", "valid-viewer-password")
    response = client.get("/racks")
    assert b"Novo Rack" not in response.data
    assert b">Editar<" not in response.data
    assert b">Excluir<" not in response.data


def test_rack_list_is_paginated_and_deterministic(
    client: FlaskClient, admin_user: User, sample_room: Room
) -> None:
    db.session.add_all(
        [
            Rack(
                room_id=sample_room.id,
                name=f"Rack {index:02d}",
                code=f"RACK-{index:02d}",
                capacity_u=42,
            )
            for index in range(RACKS_PER_PAGE + 1)
        ]
    )
    db.session.commit()
    login_admin(client)
    first = client.get("/racks")
    second = client.get("/racks?page=2")
    assert b"RACK-00" in first.data
    assert b"RACK-20" not in first.data
    assert "Próxima".encode() in first.data
    assert b"RACK-20" in second.data
    assert "Anterior".encode() in second.data
    assert client.get("/racks?page=999").status_code == 404


def test_hierarchy_is_displayed_and_user_content_is_escaped(
    client: FlaskClient,
    admin_user: User,
    sample_room: Room,
    sample_datacenter: Datacenter,
) -> None:
    rack = Rack(
        room_id=sample_room.id,
        name="<script>alert('x')</script>",
        code="RACK-XSS",
        capacity_u=42,
        description="<img src=x onerror=alert('x')>",
    )
    db.session.add(rack)
    db.session.commit()
    login_admin(client)
    detail = client.get(f"/racks/{rack.id}")
    assert b"<script>" not in detail.data
    assert b"&lt;script&gt;" in detail.data
    assert b"<img src=x" not in detail.data
    assert sample_room.code.encode() in detail.data
    assert sample_datacenter.code.encode() in detail.data
    room_detail = client.get(f"/rooms/{sample_room.id}")
    room_list = client.get("/rooms")
    datacenter_list = client.get("/datacenters")
    assert rack.code.encode() in room_detail.data
    assert f"/racks/create?room_id={sample_room.id}".encode() in room_detail.data
    assert b"<td>1</td>" in room_list.data
    assert b'<th scope="col">Racks</th>' in datacenter_list.data
    assert b"<td>1</td>" in datacenter_list.data


def test_rack_operations_are_audited_without_submitted_values(
    client: FlaskClient, admin_user: User, sample_room: Room
) -> None:
    login_admin(client)
    secret = "token=must-not-be-audited"
    client.post(
        "/racks/create", data=rack_data(sample_room.id, description=secret)
    )
    rack = db.session.scalar(db.select(Rack).where(Rack.code == "RACK-LAB-02"))
    client.post(
        f"/racks/{rack.id}/edit",
        data=rack_data(
            sample_room.id, name="Alterado", capacity_u=48, description="segredo"
        ),
    )
    client.post(f"/racks/{rack.id}/delete")
    events = db.session.scalars(
        db.select(AuditLog)
        .where(AuditLog.event_type.like("RACK.%"))
        .order_by(AuditLog.id)
    ).all()
    assert [event.event_type for event in events] == [
        AuditEventType.RACK_CREATE.value,
        AuditEventType.RACK_UPDATE.value,
        AuditEventType.RACK_DELETE.value,
    ]
    assert all(event.actor_user_id == admin_user.id for event in events)
    assert all(event.resource_type == "rack" for event in events)
    assert all(event.resource_id == rack.id for event in events)
    assert all(event.result == "success" for event in events)
    assert events[0].details == {}
    assert events[1].details == {
        "changed_fields": ["capacity_u", "description", "name"]
    }
    serialized = json.dumps([event.details for event in events])
    assert secret not in serialized
    assert "segredo" not in serialized


@pytest.mark.parametrize("operation", ["create", "update", "delete"])
def test_audit_failure_rolls_back_rack_without_false_code_conflict(
    operation: str,
    monkeypatch: pytest.MonkeyPatch,
    admin_user: User,
    sample_room: Room,
    sample_rack: Rack,
) -> None:
    def fail_audit(*args, **kwargs):
        raise IntegrityError("audit insert", {}, Exception("audit failure"))

    monkeypatch.setattr("app.rack.services.record_event", fail_audit)
    if operation == "create":
        with pytest.raises(IntegrityError) as error:
            create_rack(
                admin_user,
                room_id=sample_room.id,
                name="Rack Audit",
                code="RACK-AUDIT",
                capacity_u=42,
                description=None,
                status=RackStatus.ACTIVE.value,
            )
        assert db.session.scalar(
            db.select(Rack).where(Rack.code == "RACK-AUDIT")
        ) is None
    elif operation == "update":
        original = sample_rack.name
        with pytest.raises(IntegrityError) as error:
            update_rack(
                admin_user,
                sample_rack,
                room_id=sample_room.id,
                name="Nome rollback",
                code=sample_rack.code,
                capacity_u=sample_rack.capacity_u,
                description=sample_rack.description,
                status=sample_rack.status,
            )
        db.session.refresh(sample_rack)
        assert sample_rack.name == original
    else:
        rack_id = sample_rack.id
        with pytest.raises(IntegrityError) as error:
            delete_rack(admin_user, sample_rack)
        assert db.session.get(Rack, rack_id) is not None
    assert not isinstance(error.value, RackCodeConflictError)


def test_room_with_rack_cannot_be_deleted_by_route_or_service(
    client: FlaskClient,
    admin_user: User,
    sample_room: Room,
    sample_rack: Rack,
) -> None:
    login_admin(client)
    confirmation = client.get(f"/rooms/{sample_room.id}/delete-confirm")
    assert "não pode ser excluída".encode() in confirmation.data
    assert b"Confirmar exclus\xc3\xa3o</button>" not in confirmation.data
    response = client.post(f"/rooms/{sample_room.id}/delete")
    assert response.status_code == 302
    assert db.session.get(Room, sample_room.id) is not None
    assert db.session.get(Rack, sample_rack.id) is not None
    assert db.session.scalar(
        db.select(AuditLog).where(
            AuditLog.event_type == AuditEventType.ROOM_DELETE.value
        )
    ) is None
    with pytest.raises(RoomHasRacksError):
        delete_room(admin_user, sample_room)


def test_database_restricts_direct_room_delete(
    app: Flask, sample_room: Room, sample_rack: Rack
) -> None:
    room_id = sample_room.id
    db.session.delete(sample_room)
    with pytest.raises(IntegrityError):
        db.session.commit()
    db.session.rollback()
    assert db.session.get(Room, room_id) is not None
