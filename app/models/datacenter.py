from datetime import datetime, timezone
from enum import Enum

from sqlalchemy.orm import validates

from app.extensions import db


DATACENTER_NAME_MAX_LENGTH = 120
DATACENTER_CODE_MAX_LENGTH = 64
DATACENTER_LOCATION_MAX_LENGTH = 255
DATACENTER_DESCRIPTION_MAX_LENGTH = 1000


class DatacenterStatus(str, Enum):
    ACTIVE = "active"
    INACTIVE = "inactive"


DATACENTER_STATUS_LABELS = {
    DatacenterStatus.ACTIVE.value: "Ativo",
    DatacenterStatus.INACTIVE.value: "Inativo",
}
DATACENTER_STATUS_CHOICES = tuple(
    (status.value, DATACENTER_STATUS_LABELS[status.value])
    for status in DatacenterStatus
)
VALID_DATACENTER_STATUSES = frozenset(status.value for status in DatacenterStatus)


def utc_now() -> datetime:
    return datetime.now(timezone.utc)


def _normalize_required_text(value: str, *, field: str, max_length: int) -> str:
    if not isinstance(value, str):
        raise ValueError(f"{field} must be a string.")
    normalized_value = value.strip()
    if not normalized_value or len(normalized_value) > max_length:
        raise ValueError(f"{field} has an invalid length.")
    return normalized_value


def normalize_datacenter_name(name: str) -> str:
    return _normalize_required_text(
        name, field="Datacenter name", max_length=DATACENTER_NAME_MAX_LENGTH
    )


def normalize_datacenter_code(code: str) -> str:
    if not isinstance(code, str):
        raise ValueError("Datacenter code must be a string.")
    normalized_code = code.strip().upper()
    if not normalized_code or len(normalized_code) > DATACENTER_CODE_MAX_LENGTH:
        raise ValueError("Datacenter code has an invalid length.")
    return normalized_code


def normalize_datacenter_location(location: str) -> str:
    return _normalize_required_text(
        location,
        field="Datacenter location",
        max_length=DATACENTER_LOCATION_MAX_LENGTH,
    )


def normalize_datacenter_description(description: str | None) -> str | None:
    if description is None:
        return None
    if not isinstance(description, str):
        raise ValueError("Datacenter description must be a string.")
    normalized_description = description.strip()
    if len(normalized_description) > DATACENTER_DESCRIPTION_MAX_LENGTH:
        raise ValueError("Datacenter description has an invalid length.")
    return normalized_description or None


class Datacenter(db.Model):
    __tablename__ = "datacenters"
    __table_args__ = (
        db.UniqueConstraint("code", name="uq_datacenters_code"),
    )

    id = db.Column(db.Integer, primary_key=True)
    name = db.Column(db.String(DATACENTER_NAME_MAX_LENGTH), nullable=False)
    code = db.Column(db.String(DATACENTER_CODE_MAX_LENGTH), nullable=False)
    location = db.Column(db.String(DATACENTER_LOCATION_MAX_LENGTH), nullable=False)
    description = db.Column(db.String(DATACENTER_DESCRIPTION_MAX_LENGTH), nullable=True)
    status = db.Column(
        db.String(20),
        nullable=False,
        default=DatacenterStatus.ACTIVE.value,
        server_default=DatacenterStatus.ACTIVE.value,
    )
    created_at = db.Column(db.DateTime(timezone=True), nullable=False, default=utc_now)
    updated_at = db.Column(
        db.DateTime(timezone=True), nullable=False, default=utc_now, onupdate=utc_now
    )

    @validates("name")
    def normalize_and_validate_name(self, _key: str, name: str) -> str:
        return normalize_datacenter_name(name)

    @validates("code")
    def normalize_and_validate_code(self, _key: str, code: str) -> str:
        return normalize_datacenter_code(code)

    @validates("location")
    def normalize_and_validate_location(self, _key: str, location: str) -> str:
        return normalize_datacenter_location(location)

    @validates("description")
    def normalize_and_validate_description(
        self, _key: str, description: str | None
    ) -> str | None:
        return normalize_datacenter_description(description)

    @validates("status")
    def validate_status(
        self, _key: str, status: str | DatacenterStatus
    ) -> str:
        status_value = status.value if isinstance(status, DatacenterStatus) else status
        if status_value not in VALID_DATACENTER_STATUSES:
            raise ValueError("Datacenter status has an invalid value.")
        return status_value

    @property
    def status_label(self) -> str:
        return DATACENTER_STATUS_LABELS.get(self.status, "Status inválido")
