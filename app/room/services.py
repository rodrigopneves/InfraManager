from flask_sqlalchemy.pagination import Pagination
from sqlalchemy.exc import IntegrityError, SQLAlchemyError
from sqlalchemy.orm import selectinload

from app.audit import record_event
from app.extensions import db
from app.models import AuditEventType, Datacenter, Room, User


ROOMS_PER_PAGE = 20


class RoomCodeConflictError(ValueError):
    pass


class RoomDatacenterNotFoundError(ValueError):
    pass


def _raise_room_integrity_error(
    error: IntegrityError, datacenter_id: int
) -> None:
    db.session.rollback()
    if db.session.get(Datacenter, datacenter_id) is None:
        raise RoomDatacenterNotFoundError(
            "Selecione um Datacenter válido."
        ) from error
    raise RoomCodeConflictError(
        "Já existe uma Sala com este código no Datacenter selecionado."
    ) from error


def list_rooms(page: int) -> Pagination:
    query = (
        db.select(Room)
        .options(selectinload(Room.datacenter))
        .order_by(Room.code, Room.id)
    )
    return db.paginate(query, page=page, per_page=ROOMS_PER_PAGE, error_out=True)


def get_room_or_404(room_id: int) -> Room:
    query = (
        db.select(Room)
        .options(selectinload(Room.datacenter))
        .where(Room.id == room_id)
    )
    return db.first_or_404(query)


def list_datacenters_for_form() -> list[Datacenter]:
    return db.session.scalars(
        db.select(Datacenter).order_by(Datacenter.code, Datacenter.id)
    ).all()


def get_datacenter(datacenter_id: int) -> Datacenter:
    datacenter = db.session.get(Datacenter, datacenter_id)
    if datacenter is None:
        raise RoomDatacenterNotFoundError("Selecione um Datacenter válido.")
    return datacenter


def room_code_exists(
    datacenter_id: int, code: str, *, exclude_room_id: int | None = None
) -> bool:
    query = db.select(Room.id).where(
        Room.datacenter_id == datacenter_id, Room.code == code
    )
    if exclude_room_id is not None:
        query = query.where(Room.id != exclude_room_id)
    return db.session.scalar(query) is not None


def create_room(
    actor: User,
    *,
    datacenter_id: int,
    name: str,
    code: str,
    description: str | None,
    status: str,
) -> Room:
    datacenter = get_datacenter(datacenter_id)
    room = Room(
        datacenter=datacenter,
        name=name,
        code=code,
        description=description,
        status=status,
    )
    db.session.add(room)
    try:
        db.session.flush()
    except IntegrityError as error:
        _raise_room_integrity_error(error, datacenter_id)

    try:
        record_event(
            AuditEventType.ROOM_CREATE,
            actor=actor,
            resource_type="room",
            resource_id=room.id,
            result="success",
            commit=False,
        )
        db.session.commit()
    except SQLAlchemyError:
        db.session.rollback()
        raise
    return room


def update_room(
    actor: User,
    room: Room,
    *,
    datacenter_id: int,
    name: str,
    code: str,
    description: str | None,
    status: str,
) -> None:
    datacenter = get_datacenter(datacenter_id)
    new_values = {
        "datacenter_id": datacenter.id,
        "name": name,
        "code": code,
        "description": description,
        "status": status,
    }
    changed_fields = [
        field
        for field, value in new_values.items()
        if getattr(room, field) != value
    ]
    room.datacenter = datacenter
    room.name = name
    room.code = code
    room.description = description
    room.status = status

    try:
        db.session.flush()
    except IntegrityError as error:
        _raise_room_integrity_error(error, datacenter_id)

    try:
        record_event(
            AuditEventType.ROOM_UPDATE,
            actor=actor,
            details={"changed_fields": changed_fields},
            resource_type="room",
            resource_id=room.id,
            result="success",
            commit=False,
        )
        db.session.commit()
    except SQLAlchemyError:
        db.session.rollback()
        raise


def delete_room(actor: User, room: Room) -> None:
    room_id = room.id
    db.session.delete(room)
    try:
        record_event(
            AuditEventType.ROOM_DELETE,
            actor=actor,
            resource_type="room",
            resource_id=room_id,
            result="success",
            commit=False,
        )
        db.session.commit()
    except SQLAlchemyError:
        db.session.rollback()
        raise
