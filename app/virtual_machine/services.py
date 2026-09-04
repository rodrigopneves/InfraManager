from flask_sqlalchemy.pagination import Pagination
from sqlalchemy.exc import IntegrityError, SQLAlchemyError
from sqlalchemy.orm import selectinload

from app.audit import record_event
from app.extensions import db
from app.models import (
    Asset,
    AssetType,
    AuditEventType,
    Rack,
    Room,
    User,
    VirtualMachine,
    normalize_virtual_machine_ip_address,
    normalize_virtual_machine_name,
)


VIRTUAL_MACHINES_PER_PAGE = 20


class VirtualMachineNameConflictError(ValueError):
    pass


class VirtualMachineHostNotFoundError(ValueError):
    pass


class VirtualMachineInvalidHostError(ValueError):
    pass


class VirtualMachineInvalidIPAddressError(ValueError):
    pass


def _hierarchy_load():
    return (
        selectinload(VirtualMachine.host_asset)
        .selectinload(Asset.rack)
        .selectinload(Rack.room)
        .selectinload(Room.datacenter)
    )


def list_virtual_machines(page: int) -> Pagination:
    query = (
        db.select(VirtualMachine)
        .options(_hierarchy_load())
        .order_by(VirtualMachine.name, VirtualMachine.id)
    )
    return db.paginate(
        query, page=page, per_page=VIRTUAL_MACHINES_PER_PAGE, error_out=True
    )


def get_virtual_machine_or_404(virtual_machine_id: int) -> VirtualMachine:
    query = (
        db.select(VirtualMachine)
        .options(_hierarchy_load())
        .where(VirtualMachine.id == virtual_machine_id)
    )
    return db.first_or_404(query)


def list_eligible_hosts() -> list[Asset]:
    return db.session.scalars(
        db.select(Asset)
        .join(Asset.rack)
        .join(Rack.room)
        .options(selectinload(Asset.rack).selectinload(Rack.room).selectinload(Room.datacenter))
        .where(Asset.asset_type == AssetType.SERVER.value)
        .order_by(Asset.asset_tag, Asset.id)
    ).all()


def get_valid_host(host_asset_id: int) -> Asset:
    host = db.session.get(Asset, host_asset_id)
    if host is None:
        raise VirtualMachineHostNotFoundError("Selecione um host físico válido.")
    if host.asset_type != AssetType.SERVER.value:
        raise VirtualMachineInvalidHostError(
            "A Máquina Virtual deve pertencer a um Ativo do tipo servidor."
        )
    return host


def virtual_machine_name_exists(
    name: str, *, exclude_virtual_machine_id: int | None = None
) -> bool:
    normalized_name = normalize_virtual_machine_name(name)
    query = db.select(VirtualMachine.id).where(VirtualMachine.name == normalized_name)
    if exclude_virtual_machine_id is not None:
        query = query.where(VirtualMachine.id != exclude_virtual_machine_id)
    return db.session.scalar(query) is not None


def validate_ip_address(value: str | None) -> str | None:
    try:
        return normalize_virtual_machine_ip_address(value)
    except ValueError as error:
        raise VirtualMachineInvalidIPAddressError(
            "Informe um endereço IPv4 ou IPv6 válido."
        ) from error


def _raise_virtual_machine_integrity_error(
    error: IntegrityError, host_asset_id: int
) -> None:
    db.session.rollback()
    host = db.session.get(Asset, host_asset_id)
    if host is None:
        raise VirtualMachineHostNotFoundError(
            "Selecione um host físico válido."
        ) from error
    if host.asset_type != AssetType.SERVER.value:
        raise VirtualMachineInvalidHostError(
            "A Máquina Virtual deve pertencer a um Ativo do tipo servidor."
        ) from error
    raise VirtualMachineNameConflictError(
        "Já existe uma Máquina Virtual com este nome."
    ) from error


def create_virtual_machine(
    actor: User,
    *,
    host_asset_id: int,
    name: str,
    hostname: str | None,
    ip_address: str | None,
    operating_system: str | None,
    vcpu: int,
    memory_mb: int,
    disk_gb: int,
    environment: str,
    status: str,
    description: str | None,
) -> VirtualMachine:
    host = get_valid_host(host_asset_id)
    name = normalize_virtual_machine_name(name)
    ip_address = validate_ip_address(ip_address)
    if virtual_machine_name_exists(name):
        raise VirtualMachineNameConflictError(
            "Já existe uma Máquina Virtual com este nome."
        )
    virtual_machine = VirtualMachine(
        host_asset=host,
        name=name,
        hostname=hostname,
        ip_address=ip_address,
        operating_system=operating_system,
        vcpu=vcpu,
        memory_mb=memory_mb,
        disk_gb=disk_gb,
        environment=environment,
        status=status,
        description=description,
    )
    db.session.add(virtual_machine)
    try:
        db.session.flush()
    except IntegrityError as error:
        _raise_virtual_machine_integrity_error(error, host_asset_id)

    try:
        record_event(
            AuditEventType.VM_CREATE,
            actor=actor,
            resource_type="virtual_machine",
            resource_id=virtual_machine.id,
            result="success",
            commit=False,
        )
        db.session.commit()
    except SQLAlchemyError:
        db.session.rollback()
        raise
    return virtual_machine


def update_virtual_machine(
    actor: User,
    virtual_machine: VirtualMachine,
    *,
    host_asset_id: int,
    name: str,
    hostname: str | None,
    ip_address: str | None,
    operating_system: str | None,
    vcpu: int,
    memory_mb: int,
    disk_gb: int,
    environment: str,
    status: str,
    description: str | None,
) -> None:
    host = get_valid_host(host_asset_id)
    name = normalize_virtual_machine_name(name)
    ip_address = validate_ip_address(ip_address)
    if virtual_machine_name_exists(
        name, exclude_virtual_machine_id=virtual_machine.id
    ):
        raise VirtualMachineNameConflictError(
            "Já existe uma Máquina Virtual com este nome."
        )
    new_values = {
        "host_asset_id": host.id,
        "name": name,
        "hostname": hostname,
        "ip_address": ip_address,
        "operating_system": operating_system,
        "vcpu": vcpu,
        "memory_mb": memory_mb,
        "disk_gb": disk_gb,
        "environment": environment,
        "status": status,
        "description": description,
    }
    changed_fields = [
        field
        for field, value in new_values.items()
        if getattr(virtual_machine, field) != value
    ]
    virtual_machine.host_asset = host
    for field, value in new_values.items():
        if field != "host_asset_id":
            setattr(virtual_machine, field, value)

    try:
        db.session.flush()
    except IntegrityError as error:
        _raise_virtual_machine_integrity_error(error, host_asset_id)

    try:
        record_event(
            AuditEventType.VM_UPDATE,
            actor=actor,
            details={"changed_fields": changed_fields},
            resource_type="virtual_machine",
            resource_id=virtual_machine.id,
            result="success",
            commit=False,
        )
        db.session.commit()
    except SQLAlchemyError:
        db.session.rollback()
        raise


def delete_virtual_machine(actor: User, virtual_machine: VirtualMachine) -> None:
    virtual_machine_id = virtual_machine.id
    db.session.delete(virtual_machine)
    try:
        record_event(
            AuditEventType.VM_DELETE,
            actor=actor,
            resource_type="virtual_machine",
            resource_id=virtual_machine_id,
            result="success",
            commit=False,
        )
        db.session.commit()
    except SQLAlchemyError:
        db.session.rollback()
        raise
