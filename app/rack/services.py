from flask_sqlalchemy.pagination import Pagination
from sqlalchemy.exc import IntegrityError, SQLAlchemyError
from sqlalchemy.orm import selectinload

from app.audit import record_event
from app.extensions import db
from app.models import Asset, AuditEventType, Rack, Room, User


RACKS_PER_PAGE = 20


class RackCodeConflictError(ValueError):
    pass


class RackRoomNotFoundError(ValueError):
    pass


class RackHasAssetsError(ValueError):
    pass


class RackCapacityBelowAssetsError(ValueError):
    pass


def _raise_rack_integrity_error(error: IntegrityError, room_id: int) -> None:
    db.session.rollback()
    if db.session.get(Room, room_id) is None:
        raise RackRoomNotFoundError("Selecione uma Sala válida.") from error
    raise RackCodeConflictError(
        "Já existe um Rack com este código na Sala selecionada."
    ) from error


def list_racks(page: int) -> Pagination:
    query = (
        db.select(Rack)
        .options(
            selectinload(Rack.room).selectinload(Room.datacenter),
            selectinload(Rack.assets),
        )
        .order_by(Rack.code, Rack.id)
    )
    return db.paginate(query, page=page, per_page=RACKS_PER_PAGE, error_out=True)


def get_rack_or_404(rack_id: int) -> Rack:
    query = (
        db.select(Rack)
        .options(
            selectinload(Rack.room).selectinload(Room.datacenter),
            selectinload(Rack.assets),
        )
        .where(Rack.id == rack_id)
    )
    return db.first_or_404(query)


def list_rooms_for_form() -> list[Room]:
    return db.session.scalars(
        db.select(Room)
        .options(selectinload(Room.datacenter))
        .order_by(Room.code, Room.id)
    ).all()


def get_room(room_id: int) -> Room:
    room = db.session.get(Room, room_id)
    if room is None:
        raise RackRoomNotFoundError("Selecione uma Sala válida.")
    return room


def rack_code_exists(
    room_id: int, code: str, *, exclude_rack_id: int | None = None
) -> bool:
    query = db.select(Rack.id).where(Rack.room_id == room_id, Rack.code == code)
    if exclude_rack_id is not None:
        query = query.where(Rack.id != exclude_rack_id)
    return db.session.scalar(query) is not None


def create_rack(
    actor: User,
    *,
    room_id: int,
    name: str,
    code: str,
    capacity_u: int,
    description: str | None,
    status: str,
) -> Rack:
    room = get_room(room_id)
    rack = Rack(
        room=room,
        name=name,
        code=code,
        capacity_u=capacity_u,
        description=description,
        status=status,
    )
    db.session.add(rack)
    try:
        db.session.flush()
    except IntegrityError as error:
        _raise_rack_integrity_error(error, room_id)

    try:
        record_event(
            AuditEventType.RACK_CREATE,
            actor=actor,
            resource_type="rack",
            resource_id=rack.id,
            result="success",
            commit=False,
        )
        db.session.commit()
    except SQLAlchemyError:
        db.session.rollback()
        raise
    return rack


def update_rack(
    actor: User,
    rack: Rack,
    *,
    room_id: int,
    name: str,
    code: str,
    capacity_u: int,
    description: str | None,
    status: str,
) -> None:
    room = get_room(room_id)
    highest_occupied_unit = db.session.scalar(
        db.select(db.func.max(Asset.rack_unit_start + Asset.rack_units - 1)).where(
            Asset.rack_id == rack.id
        )
    )
    if highest_occupied_unit is not None and capacity_u < highest_occupied_unit:
        raise RackCapacityBelowAssetsError(
            "A capacidade não pode ser menor que a última U ocupada por um Ativo."
        )
    new_values = {
        "room_id": room.id,
        "name": name,
        "code": code,
        "capacity_u": capacity_u,
        "description": description,
        "status": status,
    }
    changed_fields = [
        field for field, value in new_values.items() if getattr(rack, field) != value
    ]
    rack.room = room
    rack.name = name
    rack.code = code
    rack.capacity_u = capacity_u
    rack.description = description
    rack.status = status

    try:
        db.session.flush()
    except IntegrityError as error:
        _raise_rack_integrity_error(error, room_id)

    try:
        record_event(
            AuditEventType.RACK_UPDATE,
            actor=actor,
            details={"changed_fields": changed_fields},
            resource_type="rack",
            resource_id=rack.id,
            result="success",
            commit=False,
        )
        db.session.commit()
    except SQLAlchemyError:
        db.session.rollback()
        raise


def delete_rack(actor: User, rack: Rack) -> None:
    has_assets = db.session.scalar(
        db.select(db.exists().where(Asset.rack_id == rack.id))
    )
    if has_assets:
        raise RackHasAssetsError(
            "O Rack não pode ser excluído enquanto possuir Ativos."
        )

    rack_id = rack.id
    db.session.delete(rack)
    try:
        record_event(
            AuditEventType.RACK_DELETE,
            actor=actor,
            resource_type="rack",
            resource_id=rack_id,
            result="success",
            commit=False,
        )
        db.session.commit()
    except SQLAlchemyError:
        db.session.rollback()
        raise
