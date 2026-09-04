from datetime import datetime, timezone
from enum import Enum

from sqlalchemy.orm import validates

from app.extensions import db


RACK_NAME_MAX_LENGTH = 120
RACK_CODE_MAX_LENGTH = 64
RACK_DESCRIPTION_MAX_LENGTH = 1000
RACK_CAPACITY_U_MIN = 1
RACK_CAPACITY_U_MAX = 100


class RackStatus(str, Enum):
    ACTIVE = "active"
    INACTIVE = "inactive"


RACK_STATUS_LABELS = {
    RackStatus.ACTIVE.value: "Ativo",
    RackStatus.INACTIVE.value: "Inativo",
}
RACK_STATUS_CHOICES = tuple(
    (status.value, RACK_STATUS_LABELS[status.value]) for status in RackStatus
)
VALID_RACK_STATUSES = frozenset(status.value for status in RackStatus)


def utc_now() -> datetime:
    return datetime.now(timezone.utc)


def _normalize_required_text(value: str, *, field: str, max_length: int) -> str:
    if not isinstance(value, str):
        raise ValueError(f"{field} must be a string.")
    normalized_value = value.strip()
    if not normalized_value or len(normalized_value) > max_length:
        raise ValueError(f"{field} has an invalid length.")
    return normalized_value


def normalize_rack_name(name: str) -> str:
    return _normalize_required_text(
        name, field="Rack name", max_length=RACK_NAME_MAX_LENGTH
    )


def normalize_rack_code(code: str) -> str:
    if not isinstance(code, str):
        raise ValueError("Rack code must be a string.")
    normalized_code = code.strip().upper()
    if not normalized_code or len(normalized_code) > RACK_CODE_MAX_LENGTH:
        raise ValueError("Rack code has an invalid length.")
    return normalized_code


def normalize_rack_description(description: str | None) -> str | None:
    if description is None:
        return None
    if not isinstance(description, str):
        raise ValueError("Rack description must be a string.")
    normalized_description = description.strip()
    if len(normalized_description) > RACK_DESCRIPTION_MAX_LENGTH:
        raise ValueError("Rack description has an invalid length.")
    return normalized_description or None


class Rack(db.Model):
    __tablename__ = "racks"
    __table_args__ = (
        db.UniqueConstraint("room_id", "code", name="uq_racks_room_code"),
        db.CheckConstraint(
            "capacity_u >= 1 AND capacity_u <= 100",
            name="ck_racks_capacity_u_range",
        ),
    )

    id = db.Column(db.Integer, primary_key=True)
    room_id = db.Column(
        db.Integer,
        db.ForeignKey("rooms.id", ondelete="RESTRICT"),
        nullable=False,
    )
    name = db.Column(db.String(RACK_NAME_MAX_LENGTH), nullable=False)
    code = db.Column(db.String(RACK_CODE_MAX_LENGTH), nullable=False)
    capacity_u = db.Column(db.Integer, nullable=False)
    description = db.Column(db.String(RACK_DESCRIPTION_MAX_LENGTH), nullable=True)
    status = db.Column(
        db.String(20),
        nullable=False,
        default=RackStatus.ACTIVE.value,
        server_default=RackStatus.ACTIVE.value,
    )
    created_at = db.Column(db.DateTime(timezone=True), nullable=False, default=utc_now)
    updated_at = db.Column(
        db.DateTime(timezone=True), nullable=False, default=utc_now, onupdate=utc_now
    )

    room = db.relationship("Room", back_populates="racks")

    @validates("room_id")
    def validate_room_id(self, _key: str, room_id: int) -> int:
        if not isinstance(room_id, int) or isinstance(room_id, bool) or room_id <= 0:
            raise ValueError("Rack room ID is invalid.")
        return room_id

    @validates("name")
    def normalize_and_validate_name(self, _key: str, name: str) -> str:
        return normalize_rack_name(name)

    @validates("code")
    def normalize_and_validate_code(self, _key: str, code: str) -> str:
        return normalize_rack_code(code)

    @validates("capacity_u")
    def validate_capacity_u(self, _key: str, capacity_u: int) -> int:
        if (
            not isinstance(capacity_u, int)
            or isinstance(capacity_u, bool)
            or not RACK_CAPACITY_U_MIN <= capacity_u <= RACK_CAPACITY_U_MAX
        ):
            raise ValueError("Rack capacity must be between 1 and 100 U.")
        return capacity_u

    @validates("description")
    def normalize_and_validate_description(
        self, _key: str, description: str | None
    ) -> str | None:
        return normalize_rack_description(description)

    @validates("status")
    def validate_status(self, _key: str, status: str | RackStatus) -> str:
        status_value = status.value if isinstance(status, RackStatus) else status
        if status_value not in VALID_RACK_STATUSES:
            raise ValueError("Rack status has an invalid value.")
        return status_value

    @property
    def status_label(self) -> str:
        return RACK_STATUS_LABELS.get(self.status, "Status inválido")
