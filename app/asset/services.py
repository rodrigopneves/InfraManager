from flask_sqlalchemy.pagination import Pagination
from sqlalchemy.exc import IntegrityError, SQLAlchemyError
from sqlalchemy.orm import selectinload

from app.audit import record_event
from app.extensions import db
from app.models import Asset, AuditEventType, Rack, Room, User, normalize_asset_tag


ASSETS_PER_PAGE = 20


class AssetTagConflictError(ValueError):
    pass


class AssetRackNotFoundError(ValueError):
    pass


class AssetRackCapacityError(ValueError):
    pass


class AssetRackOverlapError(ValueError):
    pass


def _raise_asset_integrity_error(error: IntegrityError, rack_id: int) -> None:
    db.session.rollback()
    if db.session.get(Rack, rack_id) is None:
        raise AssetRackNotFoundError("Selecione um Rack válido.") from error
    raise AssetTagConflictError(
        "Já existe um Ativo com este patrimônio/identificador."
    ) from error


def list_assets(page: int) -> Pagination:
    query = (
        db.select(Asset)
        .options(
            selectinload(Asset.rack)
            .selectinload(Rack.room)
            .selectinload(Room.datacenter)
        )
        .order_by(Asset.asset_tag, Asset.id)
    )
    return db.paginate(query, page=page, per_page=ASSETS_PER_PAGE, error_out=True)


def get_asset_or_404(asset_id: int) -> Asset:
    query = (
        db.select(Asset)
        .options(
            selectinload(Asset.rack)
            .selectinload(Rack.room)
            .selectinload(Room.datacenter)
        )
        .where(Asset.id == asset_id)
    )
    return db.first_or_404(query)


def list_racks_for_form() -> list[Rack]:
    return db.session.scalars(
        db.select(Rack)
        .options(selectinload(Rack.room).selectinload(Room.datacenter))
        .order_by(Rack.code, Rack.id)
    ).all()


def get_rack(rack_id: int) -> Rack:
    rack = db.session.get(Rack, rack_id)
    if rack is None:
        raise AssetRackNotFoundError("Selecione um Rack válido.")
    return rack


def asset_tag_exists(asset_tag: str, *, exclude_asset_id: int | None = None) -> bool:
    normalized_asset_tag = normalize_asset_tag(asset_tag)
    query = db.select(Asset.id).where(Asset.asset_tag == normalized_asset_tag)
    if exclude_asset_id is not None:
        query = query.where(Asset.id != exclude_asset_id)
    return db.session.scalar(query) is not None


def validate_rack_placement(
    rack: Rack,
    rack_unit_start: int,
    rack_units: int,
    *,
    exclude_asset_id: int | None = None,
) -> None:
    rack_unit_end = rack_unit_start + rack_units - 1
    if rack_unit_end > rack.capacity_u:
        raise AssetRackCapacityError(
            "A posição informada ultrapassa a capacidade do Rack."
        )

    query = db.select(Asset.id).where(
        Asset.rack_id == rack.id,
        Asset.rack_unit_start <= rack_unit_end,
        Asset.rack_unit_start + Asset.rack_units - 1 >= rack_unit_start,
    )
    if exclude_asset_id is not None:
        query = query.where(Asset.id != exclude_asset_id)
    if db.session.scalar(query) is not None:
        raise AssetRackOverlapError(
            "A posição informada sobrepõe outro Ativo neste Rack."
        )


def create_asset(
    actor: User,
    *,
    rack_id: int,
    name: str,
    asset_tag: str,
    serial_number: str | None,
    manufacturer: str | None,
    model: str | None,
    asset_type: str,
    rack_unit_start: int,
    rack_units: int,
    description: str | None,
    status: str,
) -> Asset:
    rack = get_rack(rack_id)
    asset_tag = normalize_asset_tag(asset_tag)
    if asset_tag_exists(asset_tag):
        raise AssetTagConflictError(
            "Já existe um Ativo com este patrimônio/identificador."
        )
    validate_rack_placement(rack, rack_unit_start, rack_units)
    asset = Asset(
        rack=rack,
        name=name,
        asset_tag=asset_tag,
        serial_number=serial_number,
        manufacturer=manufacturer,
        model=model,
        asset_type=asset_type,
        rack_unit_start=rack_unit_start,
        rack_units=rack_units,
        description=description,
        status=status,
    )
    db.session.add(asset)
    try:
        db.session.flush()
    except IntegrityError as error:
        _raise_asset_integrity_error(error, rack_id)

    try:
        record_event(
            AuditEventType.ASSET_CREATE,
            actor=actor,
            resource_type="asset",
            resource_id=asset.id,
            result="success",
            commit=False,
        )
        db.session.commit()
    except SQLAlchemyError:
        db.session.rollback()
        raise
    return asset


def update_asset(
    actor: User,
    asset: Asset,
    *,
    rack_id: int,
    name: str,
    asset_tag: str,
    serial_number: str | None,
    manufacturer: str | None,
    model: str | None,
    asset_type: str,
    rack_unit_start: int,
    rack_units: int,
    description: str | None,
    status: str,
) -> None:
    rack = get_rack(rack_id)
    asset_tag = normalize_asset_tag(asset_tag)
    if asset_tag_exists(asset_tag, exclude_asset_id=asset.id):
        raise AssetTagConflictError(
            "Já existe um Ativo com este patrimônio/identificador."
        )
    validate_rack_placement(
        rack,
        rack_unit_start,
        rack_units,
        exclude_asset_id=asset.id,
    )
    new_values = {
        "rack_id": rack.id,
        "name": name,
        "asset_tag": asset_tag,
        "serial_number": serial_number,
        "manufacturer": manufacturer,
        "model": model,
        "asset_type": asset_type,
        "rack_unit_start": rack_unit_start,
        "rack_units": rack_units,
        "description": description,
        "status": status,
    }
    changed_fields = [
        field for field, value in new_values.items() if getattr(asset, field) != value
    ]
    asset.rack = rack
    for field, value in new_values.items():
        if field == "rack_id":
            continue
        setattr(asset, field, value)

    try:
        db.session.flush()
    except IntegrityError as error:
        _raise_asset_integrity_error(error, rack_id)

    try:
        record_event(
            AuditEventType.ASSET_UPDATE,
            actor=actor,
            details={"changed_fields": changed_fields},
            resource_type="asset",
            resource_id=asset.id,
            result="success",
            commit=False,
        )
        db.session.commit()
    except SQLAlchemyError:
        db.session.rollback()
        raise


def delete_asset(actor: User, asset: Asset) -> None:
    asset_id = asset.id
    db.session.delete(asset)
    try:
        record_event(
            AuditEventType.ASSET_DELETE,
            actor=actor,
            resource_type="asset",
            resource_id=asset_id,
            result="success",
            commit=False,
        )
        db.session.commit()
    except SQLAlchemyError:
        db.session.rollback()
        raise
