from flask_sqlalchemy.pagination import Pagination
from sqlalchemy.exc import IntegrityError, SQLAlchemyError

from app.audit import record_event
from app.extensions import db
from app.models import AuditEventType, Datacenter, User


DATACENTERS_PER_PAGE = 20


class DatacenterCodeConflictError(ValueError):
    pass


def list_datacenters(page: int) -> Pagination:
    query = db.select(Datacenter).order_by(Datacenter.code, Datacenter.id)
    return db.paginate(
        query,
        page=page,
        per_page=DATACENTERS_PER_PAGE,
        error_out=True,
    )


def get_datacenter_or_404(datacenter_id: int) -> Datacenter:
    return db.get_or_404(Datacenter, datacenter_id)


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
