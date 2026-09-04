import json
from urllib.parse import urlparse

import pytest
from flask import Flask
from flask.testing import FlaskClient
from sqlalchemy.exc import IntegrityError

from app.asset.services import (
    ASSETS_PER_PAGE,
    AssetRackCapacityError,
    AssetRackOverlapError,
    AssetTagConflictError,
    create_asset,
    delete_asset,
    update_asset,
    validate_rack_placement,
)
from app.extensions import db
from app.models import (
    Asset,
    AssetStatus,
    AssetType,
    AuditEventType,
    AuditLog,
    Datacenter,
    Rack,
    Room,
    User,
)
from app.rack.services import (
    RackCapacityBelowAssetsError,
    RackHasAssetsError,
    delete_rack,
    update_rack,
)
from tests.helpers import complete_login


def login(client: FlaskClient, username: str, password: str) -> None:
    complete_login(client, username, password)


def login_admin(client: FlaskClient) -> None:
    login(client, "admin.demo", "valid-admin-password")


def asset_data(parent_rack_id: int, **overrides) -> dict[str, str | int]:
    data: dict[str, str | int] = {
        "rack_id": parent_rack_id,
        "name": "Servidor de Laboratório",
        "asset_tag": "SRV-LAB-02",
        "serial_number": "SN-DEMO-002",
        "manufacturer": "Fabricante Demo",
        "model": "Modelo Demo",
        "asset_type": AssetType.SERVER.value,
        "rack_unit_start": 1,
        "rack_units": 2,
        "description": "Ativo fictício para testes.",
        "status": AssetStatus.ACTIVE.value,
    }
    data.update(overrides)
    return data


def service_values(rack_id: int, **overrides) -> dict:
    return asset_data(rack_id, **overrides)


def test_asset_model_normalizes_and_builds_complete_hierarchy(
    app: Flask,
    sample_rack: Rack,
    sample_room: Room,
    sample_datacenter: Datacenter,
) -> None:
    asset = Asset(
        rack_id=sample_rack.id,
        name="  Servidor Principal  ",
        asset_tag="  srv-001  ",
        serial_number="  SN-001  ",
        manufacturer="  Fabricante  ",
        model="  Modelo  ",
        asset_type=AssetType.SERVER.value,
        rack_unit_start=41,
        rack_units=2,
        description="  Descrição.  ",
    )
    db.session.add(asset)
    db.session.commit()
    assert asset.name == "Servidor Principal"
    assert asset.asset_tag == "SRV-001"
    assert asset.serial_number == "SN-001"
    assert asset.manufacturer == "Fabricante"
    assert asset.model == "Modelo"
    assert asset.description == "Descrição."
    assert asset.status == "active"
    assert asset.type_label == "Servidor"
    assert asset.status_label == "Ativo"
    assert asset.rack_position_label == "U41-U42"
    assert asset.created_at is not None and asset.updated_at is not None
    assert asset.rack == sample_rack
    assert asset.rack.room == sample_room
    assert asset.rack.room.datacenter == sample_datacenter


def test_optional_fields_empty_and_timestamp_updates(
    app: Flask, sample_rack: Rack
) -> None:
    asset = Asset(
        rack_id=sample_rack.id, name="Ativo", asset_tag="ATV-01",
        serial_number=" ", manufacturer=" ", model=" ",
        asset_type="other", rack_unit_start=1, rack_units=1, description=" ",
    )
    db.session.add(asset)
    db.session.commit()
    original = asset.updated_at
    assert asset.serial_number is None and asset.manufacturer is None
    assert asset.model is None and asset.description is None
    assert asset.rack_position_label == "U1"
    asset.name = "Ativo atualizado"
    db.session.commit()
    assert asset.updated_at > original


@pytest.mark.parametrize("asset_type", [item.value for item in AssetType])
def test_asset_accepts_all_controlled_types(asset_type: str, sample_rack: Rack) -> None:
    asset = Asset(
        rack_id=sample_rack.id, name="Ativo", asset_tag=f"ATV-{asset_type}",
        asset_type=asset_type, rack_unit_start=1, rack_units=1,
    )
    db.session.add(asset)
    db.session.commit()
    assert asset.asset_type == asset_type


@pytest.mark.parametrize("status", [item.value for item in AssetStatus])
def test_asset_accepts_all_statuses(status: str, sample_rack: Rack) -> None:
    asset = Asset(
        rack_id=sample_rack.id, name="Ativo", asset_tag=f"ATV-{status}",
        asset_type="other", rack_unit_start=1, rack_units=1, status=status,
    )
    db.session.add(asset)
    db.session.commit()
    assert asset.status == status


@pytest.mark.parametrize(
    ("field", "value"),
    [
        ("rack_id", 0), ("name", " "), ("name", "x" * 121),
        ("asset_tag", " "), ("asset_tag", "x" * 65),
        ("serial_number", "x" * 121), ("manufacturer", "x" * 121),
        ("model", "x" * 121), ("asset_type", "invalid"),
        ("rack_unit_start", 0), ("rack_unit_start", True),
        ("rack_units", 0), ("rack_units", -1),
        ("description", "x" * 1001), ("status", "invalid"),
    ],
)
def test_asset_model_rejects_invalid_values(
    field: str, value: object, sample_rack: Rack
) -> None:
    values = service_values(sample_rack.id)
    values[field] = value
    with pytest.raises(ValueError):
        Asset(**values)


def test_asset_tag_checks_unicode_after_uppercase(sample_rack: Rack) -> None:
    with pytest.raises(ValueError, match="length"):
        Asset(
            rack_id=sample_rack.id, name="Unicode", asset_tag="ß" * 33,
            asset_type="other", rack_unit_start=1, rack_units=1,
        )


def test_database_enforces_required_fk_unique_and_checks(
    app: Flask, sample_rack: Rack
) -> None:
    assert db.session.scalar(db.text("PRAGMA foreign_keys")) == 1
    with pytest.raises(IntegrityError):
        db.session.add(Asset())
        db.session.commit()
    db.session.rollback()
    with pytest.raises(IntegrityError):
        db.session.execute(db.insert(Asset.__table__).values(**service_values(99999)))
    db.session.rollback()
    with pytest.raises(IntegrityError):
        db.session.execute(
            db.insert(Asset.__table__).values(
                **service_values(sample_rack.id, rack_unit_start=0)
            )
        )
    db.session.rollback()


def test_asset_tag_is_globally_unique_after_normalization(
    app: Flask, sample_rack: Rack, sample_datacenter: Datacenter
) -> None:
    room = Room(datacenter_id=sample_datacenter.id, name="Sala 2", code="ROOM-02")
    db.session.add(room)
    db.session.flush()
    rack = Rack(room_id=room.id, name="Rack 2", code="RACK-02", capacity_u=42)
    db.session.add(rack)
    db.session.flush()
    db.session.add(Asset(**service_values(sample_rack.id, asset_tag="GLOBAL-01")))
    db.session.commit()
    db.session.add(Asset(**service_values(rack.id, asset_tag=" global-01 ")))
    with pytest.raises(IntegrityError):
        db.session.commit()
    db.session.rollback()


@pytest.mark.parametrize(
    ("start", "units"), [(1, 1), (41, 2), (1, 42)]
)
def test_valid_rack_capacity_boundaries(
    start: int, units: int, sample_rack: Rack
) -> None:
    validate_rack_placement(sample_rack, start, units)


@pytest.mark.parametrize(
    ("start", "units"), [(42, 2), (43, 1), (1, 43)]
)
def test_positions_beyond_rack_capacity_are_rejected(
    start: int, units: int, sample_rack: Rack
) -> None:
    with pytest.raises(AssetRackCapacityError):
        validate_rack_placement(sample_rack, start, units)


def test_overlap_rules_and_different_rack_context(
    app: Flask, sample_rack: Rack, sample_room: Room
) -> None:
    db.session.add_all([
        Asset(**service_values(sample_rack.id, asset_tag="A", rack_unit_start=1, rack_units=2)),
        Asset(**service_values(sample_rack.id, asset_tag="B", rack_unit_start=3, rack_units=2)),
    ])
    db.session.commit()
    validate_rack_placement(sample_rack, 5, 2)
    for start, units in ((2, 2), (1, 1), (4, 2)):
        with pytest.raises(AssetRackOverlapError):
            validate_rack_placement(sample_rack, start, units)
    other_rack = Rack(room_id=sample_room.id, name="Outro", code="RACK-OTHER", capacity_u=42)
    db.session.add(other_rack)
    db.session.commit()
    validate_rack_placement(other_rack, 1, 4)


def test_edit_excludes_itself_but_detects_other_asset(
    sample_rack: Rack, sample_asset: Asset
) -> None:
    validate_rack_placement(
        sample_rack, 10, 2, exclude_asset_id=sample_asset.id
    )
    other = Asset(**service_values(sample_rack.id, asset_tag="OTHER", rack_unit_start=20))
    db.session.add(other)
    db.session.commit()
    with pytest.raises(AssetRackOverlapError):
        validate_rack_placement(
            sample_rack, 20, 1, exclude_asset_id=sample_asset.id
        )


def test_update_service_rejects_overlap_without_mutating_asset(
    admin_user: User, sample_rack: Rack, sample_asset: Asset
) -> None:
    other = Asset(
        **service_values(
            sample_rack.id, asset_tag="OTHER-UPDATE", rack_unit_start=20
        )
    )
    db.session.add(other)
    db.session.commit()
    with pytest.raises(AssetRackOverlapError):
        update_asset(
            admin_user,
            sample_asset,
            **service_values(
                sample_rack.id,
                asset_tag=sample_asset.asset_tag,
                rack_unit_start=20,
            ),
        )
    assert sample_asset.rack_unit_start == 10


def test_admin_crud_and_move_asset(
    client: FlaskClient, admin_user: User, sample_rack: Rack, sample_room: Room
) -> None:
    other_rack = Rack(room_id=sample_room.id, name="Destino", code="RACK-DEST", capacity_u=24)
    db.session.add(other_rack)
    db.session.commit()
    login_admin(client)
    response = client.post(
        "/assets/create", data=asset_data(sample_rack.id, name=" Ativo Novo ", asset_tag=" new-01 ")
    )
    asset = db.session.scalar(db.select(Asset).where(Asset.asset_tag == "NEW-01"))
    assert response.status_code == 302 and asset is not None
    assert asset.name == "Ativo Novo"
    assert client.get("/assets").status_code == 200
    assert client.get(f"/assets/{asset.id}").status_code == 200
    updated = client.post(
        f"/assets/{asset.id}/edit",
        data=asset_data(
            other_rack.id, name="Atualizado", asset_tag="NEW-02",
            rack_unit_start=23, rack_units=2, status="maintenance",
        ),
    )
    db.session.refresh(asset)
    assert updated.status_code == 302
    assert asset.rack_id == other_rack.id and asset.rack_unit_end == 24
    assert asset.status_label == "Manutenção"
    assert client.get(f"/assets/{asset.id}/delete-confirm").status_code == 200
    assert db.session.get(Asset, asset.id) is not None
    assert client.post(f"/assets/{asset.id}/delete").status_code == 302
    assert db.session.get(Asset, asset.id) is None


def test_query_parameter_preselects_only_valid_rack(
    client: FlaskClient, admin_user: User, sample_rack: Rack
) -> None:
    login_admin(client)
    valid = client.get(f"/assets/create?rack_id={sample_rack.id}")
    invalid = client.get("/assets/create?rack_id=99999")
    assert f'selected value="{sample_rack.id}"'.encode() in valid.data
    assert sample_rack.room.datacenter.code.encode() in valid.data
    assert b'value="99999"' not in invalid.data


@pytest.mark.parametrize(
    ("field", "value", "message"),
    [
        ("rack_id", 99999, "Not a valid choice."),
        ("name", " ", "Informe um nome válido."),
        ("asset_tag", " ", "Informe um identificador válido."),
        ("rack_unit_start", "x", "Not a valid integer value."),
        ("rack_unit_start", 0, "A posição inicial deve ser maior ou igual a 1."),
        ("rack_units", 0, "A quantidade de U deve ser maior ou igual a 1."),
        ("asset_type", "invalid", "Not a valid choice."),
        ("status", "invalid", "Not a valid choice."),
        ("description", "x" * 1001, "A descrição é muito longa."),
    ],
)
def test_form_rejects_invalid_values(
    field: str, value: object, message: str,
    client: FlaskClient, admin_user: User, sample_rack: Rack,
) -> None:
    login_admin(client)
    response = client.post(
        "/assets/create", data=asset_data(sample_rack.id, **{field: value})
    )
    assert response.status_code == 200
    assert message.encode() in response.data
    assert db.session.scalar(db.select(db.func.count()).select_from(Asset)) == 0


def test_form_reports_capacity_overlap_and_duplicate(
    client: FlaskClient, admin_user: User, sample_rack: Rack, sample_asset: Asset
) -> None:
    login_admin(client)
    capacity = client.post(
        "/assets/create", data=asset_data(sample_rack.id, rack_unit_start=42, rack_units=2)
    )
    overlap = client.post(
        "/assets/create", data=asset_data(sample_rack.id, rack_unit_start=11, rack_units=1)
    )
    duplicate = client.post(
        "/assets/create", data=asset_data(sample_rack.id, asset_tag=" srv-lab-01 ", rack_unit_start=1)
    )
    assert "ultrapassa a capacidade".encode() in capacity.data
    assert "sobrepõe outro Ativo".encode() in overlap.data
    assert "Já existe um Ativo".encode() in duplicate.data


@pytest.mark.parametrize(
    ("fixture_name", "username", "password"),
    [
        ("admin_user", "admin.demo", "valid-admin-password"),
        ("operator_user", "operator.demo", "valid-operator-password"),
        ("viewer_user", "viewer.demo", "valid-viewer-password"),
    ],
)
def test_all_roles_can_read_assets(
    fixture_name: str, username: str, password: str,
    request: pytest.FixtureRequest, client: FlaskClient, sample_asset: Asset,
) -> None:
    request.getfixturevalue(fixture_name)
    login(client, username, password)
    assert client.get("/assets").status_code == 200
    assert client.get(f"/assets/{sample_asset.id}").status_code == 200


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
        ("get", "/assets/create"), ("post", "/assets/create"),
        ("get", "/assets/{id}/edit"), ("post", "/assets/{id}/edit"),
        ("get", "/assets/{id}/delete-confirm"), ("post", "/assets/{id}/delete"),
    ],
)
def test_non_admin_roles_receive_403_for_writes(
    fixture_name: str, username: str, password: str, method: str, path_template: str,
    request: pytest.FixtureRequest, client: FlaskClient, sample_asset: Asset,
) -> None:
    request.getfixturevalue(fixture_name)
    login(client, username, password)
    response = getattr(client, method)(
        path_template.format(id=sample_asset.id), data=asset_data(sample_asset.rack_id)
    )
    assert response.status_code == 403


@pytest.mark.parametrize(
    ("method", "path"),
    [
        ("get", "/assets"), ("get", "/assets/1"), ("get", "/assets/create"),
        ("get", "/assets/1/edit"), ("get", "/assets/1/delete-confirm"),
        ("post", "/assets/1/delete"),
    ],
)
def test_unauthenticated_routes_redirect(method: str, path: str, client: FlaskClient) -> None:
    response = getattr(client, method)(path)
    assert response.status_code == 302
    assert urlparse(response.location).path == "/login"


@pytest.mark.parametrize(
    ("method", "path"),
    [
        ("get", "/assets/99999"), ("get", "/assets/99999/edit"),
        ("get", "/assets/99999/delete-confirm"), ("post", "/assets/99999/delete"),
    ],
)
def test_missing_asset_returns_404(
    method: str, path: str, client: FlaskClient, admin_user: User
) -> None:
    login_admin(client)
    assert getattr(client, method)(path).status_code == 404


def test_delete_get_is_405_and_writes_require_csrf(
    app: Flask, client: FlaskClient, admin_user: User, sample_asset: Asset
) -> None:
    login_admin(client)
    assert client.get(f"/assets/{sample_asset.id}/delete").status_code == 405
    app.config["WTF_CSRF_ENABLED"] = True
    assert client.post("/assets/create").status_code == 400
    assert client.post(f"/assets/{sample_asset.id}/edit").status_code == 400
    assert client.post(f"/assets/{sample_asset.id}/delete").status_code == 400
    assert db.session.get(Asset, sample_asset.id) is not None


def test_pagination_and_viewer_interface(
    client: FlaskClient, viewer_user: User, sample_rack: Rack
) -> None:
    db.session.add_all([
        Asset(**service_values(sample_rack.id, asset_tag=f"ASSET-{index:02d}", rack_unit_start=index * 2 + 1))
        for index in range(ASSETS_PER_PAGE + 1)
    ])
    db.session.commit()
    login(client, "viewer.demo", "valid-viewer-password")
    first = client.get("/assets")
    second = client.get("/assets?page=2")
    assert b"ASSET-00" in first.data and b"ASSET-20" not in first.data
    assert b"ASSET-20" in second.data
    assert "Próxima".encode() in first.data and "Anterior".encode() in second.data
    assert client.get("/assets?page=999").status_code == 404
    assert b"Novo Ativo" not in first.data and b">Editar<" not in first.data


def test_xss_hierarchy_and_rack_occupancy(
    client: FlaskClient, admin_user: User, sample_rack: Rack, sample_asset: Asset
) -> None:
    sample_asset.name = "<script>alert('x')</script>"
    sample_asset.description = "<img src=x onerror=alert('x')>"
    db.session.commit()
    login_admin(client)
    detail = client.get(f"/assets/{sample_asset.id}")
    rack_detail = client.get(f"/racks/{sample_rack.id}")
    assert b"<script>" not in detail.data and b"&lt;script&gt;" in detail.data
    assert b"<img src=x" not in detail.data
    assert sample_rack.room.code.encode() in detail.data
    assert sample_rack.room.datacenter.code.encode() in detail.data
    assert sample_asset.asset_tag.encode() in rack_detail.data
    assert b"Utilizado</dt><dd>2 U" in rack_detail.data
    assert b"Livre</dt><dd>40 U" in rack_detail.data
    assert f"/assets/create?rack_id={sample_rack.id}".encode() in rack_detail.data


def test_asset_operations_are_audited_without_values(
    client: FlaskClient, admin_user: User, sample_rack: Rack
) -> None:
    login_admin(client)
    secret = "token=must-not-be-audited"
    client.post("/assets/create", data=asset_data(sample_rack.id, description=secret))
    asset = db.session.scalar(db.select(Asset).where(Asset.asset_tag == "SRV-LAB-02"))
    client.post(
        f"/assets/{asset.id}/edit",
        data=asset_data(sample_rack.id, name="Alterado", rack_unit_start=3, description="segredo"),
    )
    client.post(f"/assets/{asset.id}/delete")
    events = db.session.scalars(
        db.select(AuditLog).where(AuditLog.event_type.like("ASSET.%")).order_by(AuditLog.id)
    ).all()
    assert [event.event_type for event in events] == [
        "ASSET.CREATE", "ASSET.UPDATE", "ASSET.DELETE"
    ]
    assert all(event.actor_user_id == admin_user.id for event in events)
    assert all(event.resource_type == "asset" for event in events)
    assert all(event.resource_id == asset.id and event.result == "success" for event in events)
    assert events[0].details == {} and events[2].details == {}
    assert events[1].details == {
        "changed_fields": ["description", "name", "rack_unit_start"]
    }
    serialized = json.dumps([event.details for event in events])
    assert secret not in serialized and "segredo" not in serialized


@pytest.mark.parametrize("operation", ["create", "update", "delete"])
def test_audit_failure_rolls_back_and_is_not_false_tag_conflict(
    operation: str, monkeypatch: pytest.MonkeyPatch, admin_user: User,
    sample_rack: Rack, sample_asset: Asset,
) -> None:
    def fail_audit(*args, **kwargs):
        raise IntegrityError("audit", {}, Exception("audit failure"))

    monkeypatch.setattr("app.asset.services.record_event", fail_audit)
    if operation == "create":
        with pytest.raises(IntegrityError) as error:
            create_asset(admin_user, **service_values(sample_rack.id, asset_tag="AUDIT"))
        assert db.session.scalar(db.select(Asset).where(Asset.asset_tag == "AUDIT")) is None
    elif operation == "update":
        original = sample_asset.name
        with pytest.raises(IntegrityError) as error:
            update_asset(
                admin_user, sample_asset,
                **service_values(sample_rack.id, asset_tag=sample_asset.asset_tag, name="Rollback", rack_unit_start=10),
            )
        db.session.refresh(sample_asset)
        assert sample_asset.name == original
    else:
        asset_id = sample_asset.id
        with pytest.raises(IntegrityError) as error:
            delete_asset(admin_user, sample_asset)
        assert db.session.get(Asset, asset_id) is not None
    assert not isinstance(error.value, AssetTagConflictError)


def test_rack_with_asset_cannot_be_deleted_at_any_layer(
    client: FlaskClient, admin_user: User, sample_rack: Rack, sample_asset: Asset
) -> None:
    login_admin(client)
    confirmation = client.get(f"/racks/{sample_rack.id}/delete-confirm")
    assert "não pode ser excluído".encode() in confirmation.data
    assert b"Confirmar exclus\xc3\xa3o</button>" not in confirmation.data
    assert client.post(f"/racks/{sample_rack.id}/delete").status_code == 302
    assert db.session.get(Rack, sample_rack.id) is not None
    assert db.session.get(Asset, sample_asset.id) is not None
    assert db.session.scalar(
        db.select(AuditLog).where(AuditLog.event_type == AuditEventType.RACK_DELETE.value)
    ) is None
    with pytest.raises(RackHasAssetsError):
        delete_rack(admin_user, sample_rack)
    db.session.delete(sample_rack)
    with pytest.raises(IntegrityError):
        db.session.commit()
    db.session.rollback()


def test_rack_capacity_cannot_be_reduced_below_occupied_units(
    client: FlaskClient, admin_user: User, sample_rack: Rack, sample_asset: Asset
) -> None:
    with pytest.raises(RackCapacityBelowAssetsError):
        update_rack(
            admin_user,
            sample_rack,
            room_id=sample_rack.room_id,
            name=sample_rack.name,
            code=sample_rack.code,
            capacity_u=10,
            description=sample_rack.description,
            status=sample_rack.status,
        )
    assert sample_rack.capacity_u == 42

    login_admin(client)
    response = client.post(
        f"/racks/{sample_rack.id}/edit",
        data={
            "room_id": sample_rack.room_id,
            "name": sample_rack.name,
            "code": sample_rack.code,
            "capacity_u": 10,
            "description": sample_rack.description,
            "status": sample_rack.status,
        },
    )
    assert response.status_code == 200
    assert "menor que a última U ocupada".encode() in response.data
