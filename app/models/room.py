from datetime import datetime, timezone
from enum import Enum

from sqlalchemy.orm import validates

from app.extensions import db


ROOM_NAME_MAX_LENGTH = 120
ROOM_CODE_MAX_LENGTH = 64
ROOM_DESCRIPTION_MAX_LENGTH = 1000


class RoomStatus(str, Enum):
    ACTIVE = "active"
    INACTIVE = "inactive"


ROOM_STATUS_LABELS = {
    RoomStatus.ACTIVE.value: "Ativo",
    RoomStatus.INACTIVE.value: "Inativo",
}
ROOM_STATUS_CHOICES = tuple(
    (status.value, ROOM_STATUS_LABELS[status.value]) for status in RoomStatus
)
VALID_ROOM_STATUSES = frozenset(status.value for status in RoomStatus)


def utc_now() -> datetime:
    return datetime.now(timezone.utc)


def _normalize_required_text(value: str, *, field: str, max_length: int) -> str:
    if not isinstance(value, str):
        raise ValueError(f"{field} must be a string.")
    normalized_value = value.strip()
    if not normalized_value or len(normalized_value) > max_length:
        raise ValueError(f"{field} has an invalid length.")
    return normalized_value


def normalize_room_name(name: str) -> str:
    return _normalize_required_text(
        name, field="Room name", max_length=ROOM_NAME_MAX_LENGTH
    )


def normalize_room_code(code: str) -> str:
    if not isinstance(code, str):
        raise ValueError("Room code must be a string.")
    normalized_code = code.strip().upper()
    if not normalized_code or len(normalized_code) > ROOM_CODE_MAX_LENGTH:
        raise ValueError("Room code has an invalid length.")
    return normalized_code


def normalize_room_description(description: str | None) -> str | None:
    if description is None:
        return None
    if not isinstance(description, str):
        raise ValueError("Room description must be a string.")
    normalized_description = description.strip()
    if len(normalized_description) > ROOM_DESCRIPTION_MAX_LENGTH:
        raise ValueError("Room description has an invalid length.")
    return normalized_description or None


class Room(db.Model):
    __tablename__ = "rooms"
    __table_args__ = (
        db.UniqueConstraint(
            "datacenter_id", "code", name="uq_rooms_datacenter_code"
        ),
    )

    id = db.Column(db.Integer, primary_key=True)
    datacenter_id = db.Column(
        db.Integer,
        db.ForeignKey("datacenters.id", ondelete="RESTRICT"),
        nullable=False,
    )
    name = db.Column(db.String(ROOM_NAME_MAX_LENGTH), nullable=False)
    code = db.Column(db.String(ROOM_CODE_MAX_LENGTH), nullable=False)
    description = db.Column(db.String(ROOM_DESCRIPTION_MAX_LENGTH), nullable=True)
    status = db.Column(
        db.String(20),
        nullable=False,
        default=RoomStatus.ACTIVE.value,
        server_default=RoomStatus.ACTIVE.value,
    )
    created_at = db.Column(db.DateTime(timezone=True), nullable=False, default=utc_now)
    updated_at = db.Column(
        db.DateTime(timezone=True), nullable=False, default=utc_now, onupdate=utc_now
    )

    datacenter = db.relationship("Datacenter", back_populates="rooms")

    @validates("datacenter_id")
    def validate_datacenter_id(self, _key: str, datacenter_id: int) -> int:
        if (
            not isinstance(datacenter_id, int)
            or isinstance(datacenter_id, bool)
            or datacenter_id <= 0
        ):
            raise ValueError("Room datacenter ID is invalid.")
        return datacenter_id

    @validates("name")
    def normalize_and_validate_name(self, _key: str, name: str) -> str:
        return normalize_room_name(name)

    @validates("code")
    def normalize_and_validate_code(self, _key: str, code: str) -> str:
        return normalize_room_code(code)

    @validates("description")
    def normalize_and_validate_description(
        self, _key: str, description: str | None
    ) -> str | None:
        return normalize_room_description(description)

    @validates("status")
    def validate_status(self, _key: str, status: str | RoomStatus) -> str:
        status_value = status.value if isinstance(status, RoomStatus) else status
        if status_value not in VALID_ROOM_STATUSES:
            raise ValueError("Room status has an invalid value.")
        return status_value

    @property
    def status_label(self) -> str:
        return ROOM_STATUS_LABELS.get(self.status, "Status inválido")
