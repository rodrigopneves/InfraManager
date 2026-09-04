import json
from urllib.parse import urlparse

import pytest
from flask import Flask
from flask.testing import FlaskClient
from sqlalchemy.exc import IntegrityError

from app.asset.services import (
    AssetHasVirtualMachinesError,
    delete_asset,
    update_asset,
)
from app.extensions import db
from app.models import (
    Asset,
    AssetType,
    AuditEventType,
    AuditLog,
    Rack,
    Room,
    User,
    VirtualMachine,
    VirtualMachineEnvironment,
    VirtualMachineStatus,
)
from app.virtual_machine.services import (
    VIRTUAL_MACHINES_PER_PAGE,
    VirtualMachineHostNotFoundError,
    VirtualMachineInvalidHostError,
    VirtualMachineInvalidIPAddressError,
    VirtualMachineNameConflictError,
    create_virtual_machine,
    delete_virtual_machine,
    get_valid_host,
    update_virtual_machine,
    validate_ip_address,
)


def login(client: FlaskClient, username: str, password: str) -> None:
    response = client.post(
        "/login", data={"username": username, "password": password}
    )
    assert response.status_code == 302
    assert urlparse(response.location).path == "/dashboard"


def login_admin(client: FlaskClient) -> None:
    login(client, "admin.demo", "valid-admin-password")


def vm_data(host_asset_id: int, **overrides) -> dict[str, str | int]:
    data: dict[str, str | int] = {
        "host_asset_id": host_asset_id,
        "name": "VM-LAB-02",
        "hostname": "vm-lab-02.example.test",
        "ip_address": "198.51.100.20",
        "operating_system": "Oracle Linux 9",
        "vcpu": 4,
        "memory_mb": 8192,
        "disk_gb": 120,
        "environment": "development",
        "status": "stopped",
        "description": "VM fictícia.",
    }
    data.update(overrides)
    return data


def test_model_normalizes_defaults_and_complete_hierarchy(
    sample_asset: Asset,
) -> None:
    virtual_machine = VirtualMachine(
        host_asset_id=sample_asset.id,
        name="  Vm Mista  ",
        hostname="  vm.example.test  ",
        ip_address="  2001:0db8::10  ",
        operating_system="  Ubuntu Server 24.04  ",
        vcpu=2,
        memory_mb=2048,
        disk_gb=40,
        environment=VirtualMachineEnvironment.PRODUCTION,
        description="  Demonstração  ",
    )
    db.session.add(virtual_machine)
    db.session.commit()
    assert virtual_machine.name == "Vm Mista"
    assert virtual_machine.hostname == "vm.example.test"
    assert virtual_machine.ip_address == "2001:db8::10"
    assert virtual_machine.operating_system == "Ubuntu Server 24.04"
    assert virtual_machine.description == "Demonstração"
    assert virtual_machine.status == "stopped"
    assert virtual_machine.environment_label == "Produção"
    assert virtual_machine.status_label == "Desligada"
    assert virtual_machine.memory_label == "2 GB"
    assert virtual_machine.host_asset.rack.room.datacenter is not None
    assert virtual_machine.created_at and virtual_machine.updated_at


def test_optional_values_become_none_and_timestamp_changes(
    sample_asset: Asset,
) -> None:
    virtual_machine = VirtualMachine(
        **vm_data(
            sample_asset.id,
            hostname=" ",
            ip_address=" ",
            operating_system=" ",
            description=" ",
        )
    )
    db.session.add(virtual_machine)
    db.session.commit()
    original = virtual_machine.updated_at
    assert virtual_machine.hostname is None
    assert virtual_machine.ip_address is None
    assert virtual_machine.operating_system is None
    assert virtual_machine.description is None
    virtual_machine.name = "Atualizada"
    db.session.commit()
    assert virtual_machine.updated_at > original


@pytest.mark.parametrize("environment", [item.value for item in VirtualMachineEnvironment])
def test_model_accepts_controlled_environments(
    environment: str, sample_asset: Asset
) -> None:
    virtual_machine = VirtualMachine(
        **vm_data(sample_asset.id, name=f"VM-{environment}", environment=environment)
    )
    db.session.add(virtual_machine)
    db.session.commit()
    assert virtual_machine.environment == environment


@pytest.mark.parametrize("status", [item.value for item in VirtualMachineStatus])
def test_model_accepts_controlled_statuses(status: str, sample_asset: Asset) -> None:
    virtual_machine = VirtualMachine(
        **vm_data(sample_asset.id, name=f"VM-{status}", status=status)
    )
    db.session.add(virtual_machine)
    db.session.commit()
    assert virtual_machine.status == status


@pytest.mark.parametrize(
    ("field", "value"),
    [
        ("host_asset_id", 0),
        ("name", " "),
        ("name", "x" * 121),
        ("hostname", "x" * 254),
        ("ip_address", "999.1.1.1"),
        ("operating_system", "x" * 121),
        ("vcpu", 0),
        ("vcpu", 513),
        ("vcpu", True),
        ("memory_mb", 127),
        ("memory_mb", 4_194_305),
        ("disk_gb", 0),
        ("disk_gb", 1_048_577),
        ("environment", "invalid"),
        ("status", "invalid"),
        ("description", "x" * 1001),
    ],
)
def test_model_rejects_invalid_values(
    field: str, value: object, sample_asset: Asset
) -> None:
    values = vm_data(sample_asset.id)
    values[field] = value
    with pytest.raises(ValueError):
        VirtualMachine(**values)


@pytest.mark.parametrize(
    ("field", "minimum", "maximum"),
    [("vcpu", 1, 512), ("memory_mb", 128, 4_194_304), ("disk_gb", 1, 1_048_576)],
)
def test_resource_boundaries(
    field: str, minimum: int, maximum: int, sample_asset: Asset
) -> None:
    for index, value in enumerate((minimum, maximum)):
        virtual_machine = VirtualMachine(
            **vm_data(sample_asset.id, name=f"VM-{field}-{index}", **{field: value})
        )
        db.session.add(virtual_machine)
    db.session.commit()


@pytest.mark.parametrize(
    ("value", "expected"),
    [("192.0.2.10", "192.0.2.10"), ("2001:0db8::10", "2001:db8::10"), (" ", None), (None, None)],
)
def test_service_accepts_valid_ip_addresses(value: str | None, expected: str | None) -> None:
    assert validate_ip_address(value) == expected


@pytest.mark.parametrize("value", ["arbitrario", "999.999.999.999", "2001:db8:::10"])
def test_service_rejects_invalid_ip_addresses(value: str) -> None:
    with pytest.raises(VirtualMachineInvalidIPAddressError):
        validate_ip_address(value)


def test_database_enforces_fk_unique_and_checks(sample_asset: Asset) -> None:
    assert db.session.scalar(db.text("PRAGMA foreign_keys")) == 1
    db.session.add(VirtualMachine(**vm_data(sample_asset.id, name="UNIQUE")))
    db.session.commit()
    db.session.add(VirtualMachine(**vm_data(sample_asset.id, name="UNIQUE")))
    with pytest.raises(IntegrityError):
        db.session.commit()
    db.session.rollback()
    with pytest.raises(IntegrityError):
        db.session.execute(
            db.insert(VirtualMachine.__table__).values(
                **vm_data(99999, name="BAD-FK")
            )
        )
    db.session.rollback()
    with pytest.raises(IntegrityError):
        db.session.execute(
            db.insert(VirtualMachine.__table__).values(
                **vm_data(sample_asset.id, name="BAD-CHECK", vcpu=0)
            )
        )
    db.session.rollback()


@pytest.mark.parametrize(
    "asset_type",
    [item.value for item in AssetType if item is not AssetType.SERVER],
)
def test_service_rejects_every_non_server_host(
    asset_type: str, sample_rack: Rack, admin_user: User
) -> None:
    asset = Asset(
        rack_id=sample_rack.id,
        name="Não servidor",
        asset_tag=f"HOST-{asset_type}",
        asset_type=asset_type,
        rack_unit_start=20,
        rack_units=1,
    )
    db.session.add(asset)
    db.session.commit()
    with pytest.raises(VirtualMachineInvalidHostError):
        create_virtual_machine(admin_user, **vm_data(asset.id))


def test_service_rejects_missing_host_and_accepts_server(
    sample_asset: Asset,
) -> None:
    assert get_valid_host(sample_asset.id) == sample_asset
    with pytest.raises(VirtualMachineHostNotFoundError):
        get_valid_host(99999)


def test_admin_crud_and_move_between_server_hosts(
    client: FlaskClient,
    admin_user: User,
    sample_asset: Asset,
    sample_rack: Rack,
) -> None:
    other_host = Asset(
        rack_id=sample_rack.id,
        name="Servidor destino",
        asset_tag="SRV-DEST-01",
        asset_type="server",
        rack_unit_start=20,
        rack_units=2,
    )
    db.session.add(other_host)
    db.session.commit()
    login_admin(client)
    created_response = client.post(
        "/virtual-machines/create",
        data=vm_data(sample_asset.id, name="  Vm Sem Upper  "),
    )
    virtual_machine = db.session.scalar(
        db.select(VirtualMachine).where(VirtualMachine.name == "Vm Sem Upper")
    )
    assert created_response.status_code == 302 and virtual_machine is not None
    assert client.get("/virtual-machines").status_code == 200
    assert client.get(f"/virtual-machines/{virtual_machine.id}").status_code == 200
    updated_response = client.post(
        f"/virtual-machines/{virtual_machine.id}/edit",
        data=vm_data(other_host.id, name="VM Atualizada", status="running"),
    )
    db.session.refresh(virtual_machine)
    assert updated_response.status_code == 302
    assert virtual_machine.host_asset_id == other_host.id
    assert virtual_machine.status == "running"
    assert client.get(
        f"/virtual-machines/{virtual_machine.id}/delete-confirm"
    ).status_code == 200
    assert db.session.get(VirtualMachine, virtual_machine.id) is not None
    assert client.post(
        f"/virtual-machines/{virtual_machine.id}/delete"
    ).status_code == 302
    assert db.session.get(VirtualMachine, virtual_machine.id) is None


def test_query_parameter_preselects_only_server(
    client: FlaskClient,
    admin_user: User,
    sample_asset: Asset,
    sample_rack: Rack,
) -> None:
    switch = Asset(
        rack_id=sample_rack.id,
        name="Switch",
        asset_tag="SW-LAB-01",
        asset_type="switch",
        rack_unit_start=20,
        rack_units=1,
    )
    db.session.add(switch)
    db.session.commit()
    login_admin(client)
    valid = client.get(
        f"/virtual-machines/create?host_asset_id={sample_asset.id}"
    )
    non_server = client.get(
        f"/virtual-machines/create?host_asset_id={switch.id}"
    )
    missing = client.get("/virtual-machines/create?host_asset_id=99999")
    assert f'selected value="{sample_asset.id}"'.encode() in valid.data
    assert sample_asset.rack.room.datacenter.code.encode() in valid.data
    assert switch.asset_tag.encode() not in non_server.data
    assert b'value="99999"' not in missing.data


@pytest.mark.parametrize(
    ("field", "value", "message"),
    [
        ("host_asset_id", 99999, "Not a valid choice."),
        ("name", " ", "Informe um nome válido."),
        ("hostname", "x" * 254, "máximo 253"),
        ("ip_address", "999.1.1.1", "IPv4 ou IPv6 válido"),
        ("operating_system", "x" * 121, "máximo 120"),
        ("vcpu", 0, "vCPU deve estar entre"),
        ("memory_mb", 127, "Memória deve estar entre"),
        ("disk_gb", 0, "Disco deve estar entre"),
        ("environment", "invalid", "Not a valid choice."),
        ("status", "invalid", "Not a valid choice."),
        ("description", "x" * 1001, "descrição é muito longa"),
    ],
)
def test_form_rejects_invalid_values(
    field: str,
    value: object,
    message: str,
    client: FlaskClient,
    admin_user: User,
    sample_asset: Asset,
) -> None:
    login_admin(client)
    data = vm_data(sample_asset.id)
    data[field] = value
    response = client.post(
        "/virtual-machines/create",
        data=data,
    )
    assert response.status_code == 200
    assert message.encode() in response.data
    assert db.session.scalar(
        db.select(db.func.count()).select_from(VirtualMachine)
    ) == 0


def test_duplicate_name_and_race_are_reported_as_conflict(
    monkeypatch: pytest.MonkeyPatch,
    admin_user: User,
    sample_asset: Asset,
    sample_virtual_machine: VirtualMachine,
) -> None:
    with pytest.raises(VirtualMachineNameConflictError):
        create_virtual_machine(
            admin_user,
            **vm_data(sample_asset.id, name=sample_virtual_machine.name),
        )
    monkeypatch.setattr(
        "app.virtual_machine.services.virtual_machine_name_exists",
        lambda *args, **kwargs: False,
    )
    with pytest.raises(VirtualMachineNameConflictError):
        create_virtual_machine(
            admin_user,
            **vm_data(sample_asset.id, name=sample_virtual_machine.name),
        )


@pytest.mark.parametrize(
    ("fixture_name", "username", "password"),
    [
        ("admin_user", "admin.demo", "valid-admin-password"),
        ("operator_user", "operator.demo", "valid-operator-password"),
        ("viewer_user", "viewer.demo", "valid-viewer-password"),
    ],
)
def test_all_roles_can_read(
    fixture_name: str,
    username: str,
    password: str,
    request: pytest.FixtureRequest,
    client: FlaskClient,
    sample_virtual_machine: VirtualMachine,
) -> None:
    request.getfixturevalue(fixture_name)
    login(client, username, password)
    assert client.get("/virtual-machines").status_code == 200
    assert client.get(
        f"/virtual-machines/{sample_virtual_machine.id}"
    ).status_code == 200


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
        ("get", "/virtual-machines/create"),
        ("post", "/virtual-machines/create"),
        ("get", "/virtual-machines/{id}/edit"),
        ("post", "/virtual-machines/{id}/edit"),
        ("get", "/virtual-machines/{id}/delete-confirm"),
        ("post", "/virtual-machines/{id}/delete"),
    ],
)
def test_non_admin_roles_receive_403_for_writes(
    fixture_name: str,
    username: str,
    password: str,
    method: str,
    path_template: str,
    request: pytest.FixtureRequest,
    client: FlaskClient,
    sample_virtual_machine: VirtualMachine,
) -> None:
    request.getfixturevalue(fixture_name)
    login(client, username, password)
    response = getattr(client, method)(
        path_template.format(id=sample_virtual_machine.id),
        data=vm_data(sample_virtual_machine.host_asset_id),
    )
    assert response.status_code == 403


@pytest.mark.parametrize(
    ("method", "path"),
    [
        ("get", "/virtual-machines"),
        ("get", "/virtual-machines/1"),
        ("get", "/virtual-machines/create"),
        ("get", "/virtual-machines/1/edit"),
        ("get", "/virtual-machines/1/delete-confirm"),
        ("post", "/virtual-machines/1/delete"),
    ],
)
def test_unauthenticated_routes_redirect(
    method: str, path: str, client: FlaskClient
) -> None:
    response = getattr(client, method)(path)
    assert response.status_code == 302
    assert urlparse(response.location).path == "/login"


@pytest.mark.parametrize(
    ("method", "path"),
    [
        ("get", "/virtual-machines/99999"),
        ("get", "/virtual-machines/99999/edit"),
        ("get", "/virtual-machines/99999/delete-confirm"),
        ("post", "/virtual-machines/99999/delete"),
    ],
)
def test_missing_resource_is_404(
    method: str, path: str, client: FlaskClient, admin_user: User
) -> None:
    login_admin(client)
    assert getattr(client, method)(path).status_code == 404


def test_delete_get_is_405_and_writes_require_csrf(
    app: Flask,
    client: FlaskClient,
    admin_user: User,
    sample_virtual_machine: VirtualMachine,
) -> None:
    login_admin(client)
    assert client.get(
        f"/virtual-machines/{sample_virtual_machine.id}/delete"
    ).status_code == 405
    app.config["WTF_CSRF_ENABLED"] = True
    assert client.post("/virtual-machines/create").status_code == 400
    assert client.post(
        f"/virtual-machines/{sample_virtual_machine.id}/edit"
    ).status_code == 400
    assert client.post(
        f"/virtual-machines/{sample_virtual_machine.id}/delete"
    ).status_code == 400


def test_pagination_order_and_viewer_interface(
    client: FlaskClient,
    viewer_user: User,
    sample_asset: Asset,
) -> None:
    db.session.add_all(
        [
            VirtualMachine(
                **vm_data(sample_asset.id, name=f"VM-{index:02d}")
            )
            for index in range(VIRTUAL_MACHINES_PER_PAGE + 1)
        ]
    )
    db.session.commit()
    login(client, "viewer.demo", "valid-viewer-password")
    first = client.get("/virtual-machines")
    second = client.get("/virtual-machines?page=2")
    assert b"VM-00" in first.data and b"VM-20" not in first.data
    assert b"VM-20" in second.data
    assert "Próxima".encode() in first.data
    assert "Anterior".encode() in second.data
    assert client.get("/virtual-machines?page=999").status_code == 404
    assert "Nova Máquina Virtual".encode() not in first.data
    assert b">Editar<" not in first.data


def test_xss_hierarchy_and_asset_detail(
    client: FlaskClient,
    admin_user: User,
    sample_asset: Asset,
    sample_virtual_machine: VirtualMachine,
) -> None:
    sample_virtual_machine.name = "<script>alert('x')</script>"
    sample_virtual_machine.description = "<img src=x onerror=alert('x')>"
    db.session.commit()
    login_admin(client)
    detail = client.get(f"/virtual-machines/{sample_virtual_machine.id}")
    asset_detail = client.get(f"/assets/{sample_asset.id}")
    assert b"<script>" not in detail.data and b"&lt;script&gt;" in detail.data
    assert b"<img src=x" not in detail.data
    assert sample_asset.rack.room.datacenter.code.encode() in detail.data
    assert b"Total de VMs: 1" in asset_detail.data
    creation_url = f"/virtual-machines/create?host_asset_id={sample_asset.id}"
    assert creation_url.encode() in asset_detail.data


def test_non_server_detail_has_no_vm_creation(
    client: FlaskClient,
    admin_user: User,
    sample_rack: Rack,
) -> None:
    switch = Asset(
        rack_id=sample_rack.id,
        name="Switch",
        asset_tag="SW-NO-VM",
        asset_type="switch",
        rack_unit_start=20,
        rack_units=1,
    )
    db.session.add(switch)
    db.session.commit()
    login_admin(client)
    response = client.get(f"/assets/{switch.id}")
    assert "Máquinas Virtuais</h2>".encode() not in response.data
    assert "Nova Máquina Virtual".encode() not in response.data


def test_operations_are_audited_with_allowlisted_fields_only(
    client: FlaskClient,
    admin_user: User,
    sample_asset: Asset,
) -> None:
    login_admin(client)
    secret = "token=must-not-be-audited"
    client.post(
        "/virtual-machines/create",
        data=vm_data(sample_asset.id, description=secret),
    )
    virtual_machine = db.session.scalar(
        db.select(VirtualMachine).where(VirtualMachine.name == "VM-LAB-02")
    )
    client.post(
        f"/virtual-machines/{virtual_machine.id}/edit",
        data=vm_data(
            sample_asset.id,
            hostname="alterado.example.test",
            description="segredo",
        ),
    )
    client.post(f"/virtual-machines/{virtual_machine.id}/delete")
    events = db.session.scalars(
        db.select(AuditLog)
        .where(AuditLog.event_type.like("VM.%"))
        .order_by(AuditLog.id)
    ).all()
    assert [event.event_type for event in events] == [
        "VM.CREATE",
        "VM.UPDATE",
        "VM.DELETE",
    ]
    assert all(event.actor_user_id == admin_user.id for event in events)
    assert all(event.resource_type == "virtual_machine" for event in events)
    assert all(
        event.resource_id == virtual_machine.id and event.result == "success"
        for event in events
    )
    assert events[0].details == {} and events[2].details == {}
    assert events[1].details == {
        "changed_fields": ["description", "hostname"]
    }
    serialized = json.dumps([event.details for event in events])
    assert secret not in serialized and "segredo" not in serialized


@pytest.mark.parametrize("operation", ["create", "update", "delete"])
def test_audit_failure_rolls_back_and_is_not_false_name_conflict(
    operation: str,
    monkeypatch: pytest.MonkeyPatch,
    admin_user: User,
    sample_asset: Asset,
    sample_virtual_machine: VirtualMachine,
) -> None:
    def fail_audit(*args, **kwargs):
        raise IntegrityError("audit", {}, Exception("audit failure"))

    monkeypatch.setattr("app.virtual_machine.services.record_event", fail_audit)
    if operation == "create":
        with pytest.raises(IntegrityError) as error:
            create_virtual_machine(
                admin_user, **vm_data(sample_asset.id, name="VM-AUDIT")
            )
        assert db.session.scalar(
            db.select(VirtualMachine).where(VirtualMachine.name == "VM-AUDIT")
        ) is None
    elif operation == "update":
        original = sample_virtual_machine.name
        with pytest.raises(IntegrityError) as error:
            update_virtual_machine(
                admin_user,
                sample_virtual_machine,
                **vm_data(sample_asset.id, name="Rollback"),
            )
        db.session.refresh(sample_virtual_machine)
        assert sample_virtual_machine.name == original
    else:
        virtual_machine_id = sample_virtual_machine.id
        with pytest.raises(IntegrityError) as error:
            delete_virtual_machine(admin_user, sample_virtual_machine)
        assert db.session.get(VirtualMachine, virtual_machine_id) is not None
    assert not isinstance(error.value, VirtualMachineNameConflictError)


def test_asset_with_vm_cannot_be_deleted_at_any_layer(
    client: FlaskClient,
    admin_user: User,
    sample_asset: Asset,
    sample_virtual_machine: VirtualMachine,
) -> None:
    login_admin(client)
    confirmation = client.get(f"/assets/{sample_asset.id}/delete-confirm")
    assert "não pode ser excluído".encode() in confirmation.data
    assert "Confirmar exclusão</button>".encode() not in confirmation.data
    assert client.post(f"/assets/{sample_asset.id}/delete").status_code == 302
    assert db.session.get(Asset, sample_asset.id) is not None
    assert db.session.get(VirtualMachine, sample_virtual_machine.id) is not None
    assert db.session.scalar(
        db.select(AuditLog).where(
            AuditLog.event_type == AuditEventType.ASSET_DELETE.value
        )
    ) is None
    with pytest.raises(AssetHasVirtualMachinesError):
        delete_asset(admin_user, sample_asset)
    db.session.delete(sample_asset)
    with pytest.raises(IntegrityError):
        db.session.commit()
    db.session.rollback()


def test_asset_without_vm_remains_deletable(
    admin_user: User, sample_asset: Asset
) -> None:
    asset_id = sample_asset.id
    delete_asset(admin_user, sample_asset)
    assert db.session.get(Asset, asset_id) is None


def test_host_with_vm_cannot_be_changed_to_non_server(
    client: FlaskClient,
    admin_user: User,
    sample_asset: Asset,
    sample_virtual_machine: VirtualMachine,
) -> None:
    values = {
        "rack_id": sample_asset.rack_id,
        "name": sample_asset.name,
        "asset_tag": sample_asset.asset_tag,
        "serial_number": sample_asset.serial_number,
        "manufacturer": sample_asset.manufacturer,
        "model": sample_asset.model,
        "asset_type": "switch",
        "rack_unit_start": sample_asset.rack_unit_start,
        "rack_units": sample_asset.rack_units,
        "description": sample_asset.description,
        "status": sample_asset.status,
    }
    with pytest.raises(AssetHasVirtualMachinesError):
        update_asset(admin_user, sample_asset, **values)
    assert sample_asset.asset_type == "server"
    assert db.session.scalar(
        db.select(AuditLog).where(
            AuditLog.event_type == AuditEventType.ASSET_UPDATE.value
        )
    ) is None

    login_admin(client)
    response = client.post(f"/assets/{sample_asset.id}/edit", data=values)
    assert response.status_code == 200
    assert "não pode ser alterado".encode() in response.data
    db.session.refresh(sample_asset)
    assert sample_asset.asset_type == "server"
