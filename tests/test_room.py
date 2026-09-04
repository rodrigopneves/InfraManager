import json
from urllib.parse import urlparse

import pytest
from flask import Flask
from flask.testing import FlaskClient
from sqlalchemy.exc import IntegrityError

from app.datacenter.services import DatacenterHasRoomsError, delete_datacenter
from app.extensions import db
from app.models import (
    AuditEventType,
    AuditLog,
    Datacenter,
    Room,
    RoomStatus,
    User,
)
from app.room.services import (
    ROOMS_PER_PAGE,
    RoomCodeConflictError,
    create_room,
    update_room,
    delete_room,
)


def login(client: FlaskClient, username: str, password: str) -> None:
    response = client.post(
        "/login", data={"username": username, "password": password}
    )
    assert response.status_code == 302
    assert urlparse(response.location).path == "/dashboard"


def login_admin(client: FlaskClient) -> None:
    login(client, "admin.demo", "valid-admin-password")


def room_data(parent_datacenter_id: int, **overrides) -> dict[str, str | int]:
    data: dict[str, str | int] = {
        "datacenter_id": parent_datacenter_id,
        "name": "Sala de Laboratório",
        "code": "ROOM-LAB-02",
        "description": "Ambiente fictício para testes.",
        "status": RoomStatus.ACTIVE.value,
    }
    data.update(overrides)
    return data


def test_room_model_normalizes_values_and_sets_defaults(
    app: Flask, sample_datacenter: Datacenter
) -> None:
    room = Room(
        datacenter_id=sample_datacenter.id,
        name="  Sala Principal  ",
        code="  room-01  ",
        description="  Descrição fictícia.  ",
    )
    db.session.add(room)
    db.session.commit()

    assert room.name == "Sala Principal"
    assert room.code == "ROOM-01"
    assert room.description == "Descrição fictícia."
    assert room.status == RoomStatus.ACTIVE.value
    assert room.status_label == "Ativo"
    assert room.created_at is not None
    assert room.updated_at is not None
    assert room.datacenter == sample_datacenter


def test_room_updated_at_changes_and_empty_description_becomes_none(
    app: Flask, sample_datacenter: Datacenter
) -> None:
    room = Room(
        datacenter_id=sample_datacenter.id,
        name="Sala Original",
        code="ROOM-TIMESTAMP",
        description="   ",
    )
    db.session.add(room)
    db.session.commit()
    original_updated_at = room.updated_at
    assert room.description is None
    room.name = "Sala Atualizada"
    db.session.commit()
    assert room.updated_at > original_updated_at


@pytest.mark.parametrize("status", ["active", "inactive"])
def test_room_accepts_supported_statuses(
    status: str, sample_datacenter: Datacenter
) -> None:
    room = Room(
        datacenter_id=sample_datacenter.id,
        name="Sala Status",
        code=f"ROOM-{status}",
        status=status,
    )
    db.session.add(room)
    db.session.commit()
    assert room.status == status


@pytest.mark.parametrize(
    ("field", "value"),
    [
        ("name", "   "),
        ("code", "   "),
        ("name", "x" * 121),
        ("code", "x" * 65),
        ("description", "x" * 1001),
        ("status", "maintenance"),
        ("datacenter_id", 0),
    ],
)
def test_room_model_rejects_invalid_values(
    field: str, value: str | int, sample_datacenter: Datacenter
) -> None:
    values = {
        "datacenter_id": sample_datacenter.id,
        "name": "Sala válida",
        "code": "ROOM-VALID",
        "description": None,
        "status": RoomStatus.ACTIVE.value,
    }
    values[field] = value
    with pytest.raises(ValueError):
        Room(**values)


def test_code_length_is_checked_after_unicode_uppercase_expansion(
    sample_datacenter: Datacenter,
) -> None:
    with pytest.raises(ValueError, match="length"):
        Room(
            datacenter_id=sample_datacenter.id,
            name="Sala Unicode",
            code="ß" * 33,
        )


def test_room_code_is_unique_only_inside_same_datacenter(
    app: Flask, sample_datacenter: Datacenter
) -> None:
    other_datacenter = Datacenter(
        name="Datacenter Dois", code="DC-LAB-02", location="Curitiba"
    )
    db.session.add(other_datacenter)
    db.session.flush()
    db.session.add_all(
        [
            Room(
                datacenter_id=sample_datacenter.id,
                name="Sala Um",
                code="ROOM-01",
            ),
            Room(
                datacenter_id=other_datacenter.id,
                name="Sala Dois",
                code="room-01",
            ),
        ]
    )
    db.session.commit()

    db.session.add(
        Room(
            datacenter_id=sample_datacenter.id,
            name="Sala Duplicada",
            code=" room-01 ",
        )
    )
    with pytest.raises(IntegrityError):
        db.session.commit()
    db.session.rollback()


def test_sqlite_foreign_keys_reject_missing_parent(app: Flask) -> None:
    assert db.session.scalar(db.text("PRAGMA foreign_keys")) == 1
    db.session.add(Room(datacenter_id=99999, name="Órfã", code="ROOM-ORPHAN"))
    with pytest.raises(IntegrityError):
        db.session.commit()
    db.session.rollback()


def test_database_enforces_required_room_columns(app: Flask) -> None:
    db.session.add(Room())
    with pytest.raises(IntegrityError):
        db.session.commit()
    db.session.rollback()


def test_existing_audit_foreign_key_set_null_still_works(
    app: Flask, admin_user: User
) -> None:
    audit_log = AuditLog(
        event_type=AuditEventType.LOGOUT,
        actor_user_id=admin_user.id,
        details={},
    )
    db.session.add(audit_log)
    db.session.commit()
    db.session.delete(admin_user)
    db.session.commit()
    db.session.refresh(audit_log)
    assert audit_log.actor_user_id is None


def test_admin_can_create_read_update_and_delete_room(
    client: FlaskClient, admin_user: User, sample_datacenter: Datacenter
) -> None:
    login_admin(client)
    create_response = client.post(
        "/rooms/create",
        data=room_data(
            sample_datacenter.id,
            name="  Sala Nova  ",
            code="  room-new-01  ",
            description="  Texto controlado.  ",
        ),
    )
    created = db.session.scalar(
        db.select(Room).where(Room.code == "ROOM-NEW-01")
    )
    assert create_response.status_code == 302
    assert created is not None
    assert created.name == "Sala Nova"
    assert created.description == "Texto controlado."
    assert client.get("/rooms").status_code == 200
    assert client.get(f"/rooms/{created.id}").status_code == 200

    update_response = client.post(
        f"/rooms/{created.id}/edit",
        data=room_data(
            sample_datacenter.id,
            name="Sala Atualizada",
            code="ROOM-UPDATED",
            status=RoomStatus.INACTIVE.value,
        ),
    )
    db.session.refresh(created)
    assert update_response.status_code == 302
    assert created.name == "Sala Atualizada"
    assert created.code == "ROOM-UPDATED"
    assert created.status_label == "Inativo"

    confirmation = client.get(f"/rooms/{created.id}/delete-confirm")
    assert confirmation.status_code == 200
    assert db.session.get(Room, created.id) is not None
    delete_response = client.post(f"/rooms/{created.id}/delete")
    assert delete_response.status_code == 302
    assert db.session.get(Room, created.id) is None


def test_create_query_preselects_only_existing_datacenter(
    client: FlaskClient, admin_user: User, sample_datacenter: Datacenter
) -> None:
    login_admin(client)
    response = client.get(
        f"/rooms/create?datacenter_id={sample_datacenter.id}"
    )
    invalid = client.get("/rooms/create?datacenter_id=99999")
    assert response.status_code == 200
    assert f'selected value="{sample_datacenter.id}"'.encode() in response.data
    assert invalid.status_code == 200
    assert b'value="99999"' not in invalid.data


def test_room_can_move_when_code_is_available_and_conflict_is_rejected(
    client: FlaskClient,
    admin_user: User,
    sample_datacenter: Datacenter,
    sample_room: Room,
) -> None:
    other = Datacenter(name="DC Dois", code="DC-02", location="Recife")
    db.session.add(other)
    db.session.commit()
    db.session.add(Room(datacenter_id=other.id, name="Ocupada", code="USED"))
    db.session.commit()
    login_admin(client)

    moved = client.post(
        f"/rooms/{sample_room.id}/edit",
        data=room_data(other.id, code="FREE"),
    )
    assert moved.status_code == 302
    db.session.refresh(sample_room)
    assert sample_room.datacenter_id == other.id

    conflict = client.post(
        f"/rooms/{sample_room.id}/edit",
        data=room_data(other.id, code=" used "),
    )
    db.session.refresh(sample_room)
    assert conflict.status_code == 200
    assert "Já existe uma Sala".encode() in conflict.data
    assert sample_room.code == "FREE"


@pytest.mark.parametrize(
    ("field", "value", "message"),
    [
        ("name", "   ", "Informe um nome válido."),
        ("code", "   ", "Informe um código válido."),
        ("description", "x" * 1001, "A descrição é muito longa."),
        ("status", "maintenance", "Not a valid choice."),
        ("datacenter_id", 99999, "Not a valid choice."),
    ],
)
def test_create_rejects_invalid_form_values(
    field: str,
    value: str | int,
    message: str,
    client: FlaskClient,
    admin_user: User,
    sample_datacenter: Datacenter,
) -> None:
    login_admin(client)
    response = client.post(
        "/rooms/create", data=room_data(sample_datacenter.id, **{field: value})
    )
    assert response.status_code == 200
    assert message.encode() in response.data
    assert db.session.scalar(db.select(db.func.count()).select_from(Room)) == 0


@pytest.mark.parametrize(
    ("fixture_name", "username", "password"),
    [
        ("admin_user", "admin.demo", "valid-admin-password"),
        ("operator_user", "operator.demo", "valid-operator-password"),
        ("viewer_user", "viewer.demo", "valid-viewer-password"),
    ],
)
def test_all_roles_can_list_and_view_rooms(
    fixture_name: str,
    username: str,
    password: str,
    request: pytest.FixtureRequest,
    client: FlaskClient,
    sample_room: Room,
) -> None:
    request.getfixturevalue(fixture_name)
    login(client, username, password)
    assert client.get("/rooms").status_code == 200
    assert client.get(f"/rooms/{sample_room.id}").status_code == 200


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
        ("get", "/rooms/create"),
        ("post", "/rooms/create"),
        ("get", "/rooms/{id}/edit"),
        ("post", "/rooms/{id}/edit"),
        ("get", "/rooms/{id}/delete-confirm"),
        ("post", "/rooms/{id}/delete"),
    ],
)
def test_non_admin_roles_receive_403_for_room_writes(
    fixture_name: str,
    username: str,
    password: str,
    method: str,
    path_template: str,
    request: pytest.FixtureRequest,
    client: FlaskClient,
    sample_room: Room,
) -> None:
    request.getfixturevalue(fixture_name)
    login(client, username, password)
    response = getattr(client, method)(
        path_template.format(id=sample_room.id),
        data=room_data(sample_room.datacenter_id),
    )
    assert response.status_code == 403


def test_room_delete_does_not_accept_get_and_writes_require_csrf(
    app: Flask,
    client: FlaskClient,
    admin_user: User,
    sample_room: Room,
) -> None:
    login_admin(client)
    assert client.get(f"/rooms/{sample_room.id}/delete").status_code == 405
    app.config["WTF_CSRF_ENABLED"] = True
    assert client.post("/rooms/create", data={}).status_code == 400
    assert client.post(f"/rooms/{sample_room.id}/edit", data={}).status_code == 400
    assert client.post(f"/rooms/{sample_room.id}/delete").status_code == 400
    assert db.session.get(Room, sample_room.id) is not None


@pytest.mark.parametrize(
    ("method", "path"),
    [
        ("get", "/rooms/99999"),
        ("get", "/rooms/99999/edit"),
        ("get", "/rooms/99999/delete-confirm"),
        ("post", "/rooms/99999/delete"),
    ],
)
def test_missing_room_returns_404(
    method: str, path: str, client: FlaskClient, admin_user: User
) -> None:
    login_admin(client)
    assert getattr(client, method)(path).status_code == 404


@pytest.mark.parametrize(
    ("method", "path"),
    [
        ("get", "/rooms"),
        ("get", "/rooms/1"),
        ("get", "/rooms/create"),
        ("get", "/rooms/1/edit"),
        ("get", "/rooms/1/delete-confirm"),
        ("post", "/rooms/1/delete"),
    ],
)
def test_unauthenticated_room_routes_redirect_to_login(
    method: str, path: str, client: FlaskClient
) -> None:
    response = getattr(client, method)(path)
    assert response.status_code == 302
    assert urlparse(response.location).path == "/login"


def test_viewer_interface_hides_room_mutating_actions(
    client: FlaskClient, viewer_user: User, sample_room: Room
) -> None:
    login(client, "viewer.demo", "valid-viewer-password")
    response = client.get("/rooms")
    assert b"Nova Sala" not in response.data
    assert b">Editar<" not in response.data
    assert b">Excluir<" not in response.data


def test_room_list_is_paginated(
    client: FlaskClient, admin_user: User, sample_datacenter: Datacenter
) -> None:
    db.session.add_all(
        [
            Room(
                datacenter_id=sample_datacenter.id,
                name=f"Sala {index:02d}",
                code=f"ROOM-{index:02d}",
            )
            for index in range(ROOMS_PER_PAGE + 1)
        ]
    )
    db.session.commit()
    login_admin(client)
    first = client.get("/rooms")
    second = client.get("/rooms?page=2")
    assert b"ROOM-00" in first.data
    assert b"ROOM-20" not in first.data
    assert "Próxima".encode() in first.data
    assert b"ROOM-20" in second.data
    assert "Anterior".encode() in second.data
    assert client.get("/rooms?page=999").status_code == 404


def test_datacenter_pages_show_room_count_and_link(
    client: FlaskClient,
    admin_user: User,
    sample_datacenter: Datacenter,
    sample_room: Room,
) -> None:
    login_admin(client)
    listing = client.get("/datacenters")
    detail = client.get(f"/datacenters/{sample_datacenter.id}")
    assert b"<td>1</td>" in listing.data
    assert sample_room.code.encode() in detail.data
    assert f"/rooms/{sample_room.id}".encode() in detail.data
    assert (
        f"/rooms/create?datacenter_id={sample_datacenter.id}".encode()
        in detail.data
    )


def test_user_content_is_escaped_in_room_and_datacenter_templates(
    client: FlaskClient, admin_user: User, sample_datacenter: Datacenter
) -> None:
    room = Room(
        datacenter_id=sample_datacenter.id,
        name="<script>alert('x')</script>",
        code="ROOM-XSS",
        description="<img src=x onerror=alert('x')>",
    )
    db.session.add(room)
    db.session.commit()
    login_admin(client)
    for path in (f"/rooms/{room.id}", f"/datacenters/{sample_datacenter.id}"):
        response = client.get(path)
        assert b"<script>" not in response.data
        assert b"&lt;script&gt;" in response.data


def test_room_operations_are_audited_without_submitted_values(
    client: FlaskClient, admin_user: User, sample_datacenter: Datacenter
) -> None:
    login_admin(client)
    secret = "token=must-not-be-audited"
    client.post(
        "/rooms/create",
        data=room_data(sample_datacenter.id, description=secret),
    )
    room = db.session.scalar(db.select(Room).where(Room.code == "ROOM-LAB-02"))
    client.post(
        f"/rooms/{room.id}/edit",
        data=room_data(sample_datacenter.id, name="Alterada", description="segredo"),
    )
    client.post(f"/rooms/{room.id}/delete")
    events = db.session.scalars(
        db.select(AuditLog)
        .where(AuditLog.event_type.like("ROOM.%"))
        .order_by(AuditLog.id)
    ).all()
    assert [event.event_type for event in events] == [
        AuditEventType.ROOM_CREATE.value,
        AuditEventType.ROOM_UPDATE.value,
        AuditEventType.ROOM_DELETE.value,
    ]
    assert all(event.actor_user_id == admin_user.id for event in events)
    assert all(event.resource_type == "room" for event in events)
    assert all(event.resource_id == room.id for event in events)
    assert all(event.result == "success" for event in events)
    assert events[0].details == {}
    assert events[1].details == {"changed_fields": ["description", "name"]}
    serialized = json.dumps([event.details for event in events])
    assert secret not in serialized
    assert "segredo" not in serialized


@pytest.mark.parametrize("operation", ["create", "update"])
def test_audit_failure_rolls_back_room_and_is_not_a_code_conflict(
    operation: str,
    monkeypatch: pytest.MonkeyPatch,
    admin_user: User,
    sample_datacenter: Datacenter,
    sample_room: Room,
) -> None:
    def fail_audit(*args, **kwargs):
        raise IntegrityError("audit insert", {}, Exception("audit failure"))

    monkeypatch.setattr("app.room.services.record_event", fail_audit)
    if operation == "create":
        with pytest.raises(IntegrityError) as error:
            create_room(
                admin_user,
                datacenter_id=sample_datacenter.id,
                name="Sala Audit",
                code="ROOM-AUDIT",
                description=None,
                status=RoomStatus.ACTIVE.value,
            )
        assert db.session.scalar(
            db.select(Room).where(Room.code == "ROOM-AUDIT")
        ) is None
    else:
        original_name = sample_room.name
        with pytest.raises(IntegrityError) as error:
            update_room(
                admin_user,
                sample_room,
                datacenter_id=sample_datacenter.id,
                name="Nome com rollback",
                code=sample_room.code,
                description=sample_room.description,
                status=sample_room.status,
            )
        db.session.refresh(sample_room)
        assert sample_room.name == original_name
    assert not isinstance(error.value, RoomCodeConflictError)


def test_audit_failure_rolls_back_room_delete(
    monkeypatch: pytest.MonkeyPatch, admin_user: User, sample_room: Room
) -> None:
    room_id = sample_room.id

    def fail_audit(*args, **kwargs):
        raise IntegrityError("audit insert", {}, Exception("audit failure"))

    monkeypatch.setattr("app.room.services.record_event", fail_audit)
    with pytest.raises(IntegrityError):
        delete_room(admin_user, sample_room)
    assert db.session.get(Room, room_id) is not None


def test_datacenter_with_rooms_cannot_be_deleted_by_route_or_service(
    client: FlaskClient,
    admin_user: User,
    sample_datacenter: Datacenter,
    sample_room: Room,
) -> None:
    login_admin(client)
    confirmation = client.get(
        f"/datacenters/{sample_datacenter.id}/delete-confirm"
    )
    assert "não pode ser excluído".encode() in confirmation.data
    assert b"Confirmar exclus\xc3\xa3o</button>" not in confirmation.data
    response = client.post(f"/datacenters/{sample_datacenter.id}/delete")
    assert response.status_code == 302
    assert db.session.get(Datacenter, sample_datacenter.id) is not None
    assert db.session.get(Room, sample_room.id) is not None
    assert db.session.scalar(
        db.select(AuditLog).where(
            AuditLog.event_type == AuditEventType.DATACENTER_DELETE.value
        )
    ) is None
    with pytest.raises(DatacenterHasRoomsError):
        delete_datacenter(admin_user, sample_datacenter)


def test_database_restricts_direct_datacenter_delete(
    app: Flask, sample_datacenter: Datacenter, sample_room: Room
) -> None:
    datacenter_id = sample_datacenter.id
    db.session.delete(sample_datacenter)
    with pytest.raises(IntegrityError):
        db.session.commit()
    db.session.rollback()
    assert db.session.get(Datacenter, datacenter_id) is not None
