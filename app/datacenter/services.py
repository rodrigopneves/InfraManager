from flask_sqlalchemy.pagination import Pagination
from sqlalchemy.exc import IntegrityError, SQLAlchemyError
from sqlalchemy.orm import selectinload

from app.audit import record_event
from app.extensions import db
from app.models import AuditEventType, Datacenter, Rack, Room, User


DATACENTERS_PER_PAGE = 20


class DatacenterCodeConflictError(ValueError):
    pass


class DatacenterHasRoomsError(ValueError):
    pass


def list_datacenters(page: int) -> Pagination:
    query = (
        db.select(Datacenter)
        .options(selectinload(Datacenter.rooms))
        .order_by(Datacenter.code, Datacenter.id)
    )
    return db.paginate(
        query,
        page=page,
        per_page=DATACENTERS_PER_PAGE,
        error_out=True,
    )


def get_datacenter_rack_counts(datacenter_ids: list[int]) -> dict[int, int]:
    if not datacenter_ids:
        return {}
    rows = db.session.execute(
        db.select(Room.datacenter_id, db.func.count(Rack.id))
        .select_from(Room)
        .outerjoin(Rack, Rack.room_id == Room.id)
        .where(Room.datacenter_id.in_(datacenter_ids))
        .group_by(Room.datacenter_id)
    )
    return {datacenter_id: count for datacenter_id, count in rows}


def get_datacenter_or_404(datacenter_id: int) -> Datacenter:
    query = (
        db.select(Datacenter)
        .options(selectinload(Datacenter.rooms))
        .where(Datacenter.id == datacenter_id)
    )
    return db.first_or_404(query)


def datacenter_code_exists(
    code: str, *, exclude_datacenter_id: int | None = None
) -> bool:
    query = db.select(Datacenter.id).where(Datacenter.code == code)
    if exclude_datacenter_id is not None:
        query = query.where(Datacenter.id != exclude_datacenter_id)
    return db.session.scalar(query) is not None


def create_datacenter(
    actor: User,
    *,
    name: str,
    code: str,
    location: str,
    description: str | None,
    status: str,
) -> Datacenter:
    datacenter = Datacenter(
        name=name,
        code=code,
        location=location,
        description=description,
        status=status,
    )
    db.session.add(datacenter)
    try:
        db.session.flush()
    except IntegrityError as error:
        db.session.rollback()
        raise DatacenterCodeConflictError(
            "Já existe um Datacenter com este código."
        ) from error

    try:
        record_event(
            AuditEventType.DATACENTER_CREATE,
            actor=actor,
            resource_type="datacenter",
            resource_id=datacenter.id,
            result="success",
            commit=False,
        )
        db.session.commit()
    except SQLAlchemyError:
        db.session.rollback()
        raise
    return datacenter


def update_datacenter(
    actor: User,
    datacenter: Datacenter,
    *,
    name: str,
    code: str,
    location: str,
    description: str | None,
    status: str,
) -> None:
    new_values = {
        "name": name,
        "code": code,
        "location": location,
        "description": description,
        "status": status,
    }
    changed_fields = [
        field
        for field, value in new_values.items()
        if getattr(datacenter, field) != value
    ]
    for field, value in new_values.items():
        setattr(datacenter, field, value)

    try:
        db.session.flush()
    except IntegrityError as error:
        db.session.rollback()
        raise DatacenterCodeConflictError(
            "Já existe um Datacenter com este código."
        ) from error

    try:
        record_event(
            AuditEventType.DATACENTER_UPDATE,
            actor=actor,
            details={"changed_fields": changed_fields},
            resource_type="datacenter",
            resource_id=datacenter.id,
            result="success",
            commit=False,
        )
        db.session.commit()
    except SQLAlchemyError:
        db.session.rollback()
        raise


def delete_datacenter(actor: User, datacenter: Datacenter) -> None:
    has_rooms = db.session.scalar(
        db.select(db.exists().where(Room.datacenter_id == datacenter.id))
    )
    if has_rooms:
        raise DatacenterHasRoomsError(
            "O Datacenter não pode ser excluído enquanto possuir Salas."
        )

    datacenter_id = datacenter.id
    db.session.delete(datacenter)
    try:
        record_event(
            AuditEventType.DATACENTER_DELETE,
            actor=actor,
            resource_type="datacenter",
            resource_id=datacenter_id,
            result="success",
            commit=False,
        )
        db.session.commit()
    except SQLAlchemyError:
        db.session.rollback()
        raise
