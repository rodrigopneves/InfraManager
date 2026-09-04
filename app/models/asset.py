from datetime import datetime, timezone
from enum import Enum

from sqlalchemy.orm import validates

from app.extensions import db


ASSET_NAME_MAX_LENGTH = 120
ASSET_TAG_MAX_LENGTH = 64
ASSET_OPTIONAL_TEXT_MAX_LENGTH = 120
ASSET_DESCRIPTION_MAX_LENGTH = 1000


class AssetType(str, Enum):
    SERVER = "server"
    SWITCH = "switch"
    ROUTER = "router"
    FIREWALL = "firewall"
    STORAGE = "storage"
    APPLIANCE = "appliance"
    ACCESS_POINT = "access_point"
    NOTEBOOK = "notebook"
    DESKTOP = "desktop"
    OTHER = "other"


ASSET_TYPE_LABELS = {
    AssetType.SERVER.value: "Servidor",
    AssetType.SWITCH.value: "Switch",
    AssetType.ROUTER.value: "Roteador",
    AssetType.FIREWALL.value: "Firewall",
    AssetType.STORAGE.value: "Storage",
    AssetType.APPLIANCE.value: "Appliance",
    AssetType.ACCESS_POINT.value: "Access Point",
    AssetType.NOTEBOOK.value: "Notebook",
    AssetType.DESKTOP.value: "Desktop",
    AssetType.OTHER.value: "Outro",
}
ASSET_TYPE_CHOICES = tuple(
    (asset_type.value, ASSET_TYPE_LABELS[asset_type.value])
    for asset_type in AssetType
)
VALID_ASSET_TYPES = frozenset(asset_type.value for asset_type in AssetType)


class AssetStatus(str, Enum):
    ACTIVE = "active"
    INACTIVE = "inactive"
    MAINTENANCE = "maintenance"


ASSET_STATUS_LABELS = {
    AssetStatus.ACTIVE.value: "Ativo",
    AssetStatus.INACTIVE.value: "Inativo",
    AssetStatus.MAINTENANCE.value: "Manutenção",
}
ASSET_STATUS_CHOICES = tuple(
    (status.value, ASSET_STATUS_LABELS[status.value]) for status in AssetStatus
)
VALID_ASSET_STATUSES = frozenset(status.value for status in AssetStatus)


def utc_now() -> datetime:
    return datetime.now(timezone.utc)


def _normalize_required_text(value: str, *, field: str, max_length: int) -> str:
    if not isinstance(value, str):
        raise ValueError(f"{field} must be a string.")
    normalized = value.strip()
    if not normalized or len(normalized) > max_length:
        raise ValueError(f"{field} has an invalid length.")
    return normalized


def _normalize_optional_text(
    value: str | None, *, field: str, max_length: int
) -> str | None:
    if value is None:
        return None
    if not isinstance(value, str):
        raise ValueError(f"{field} must be a string.")
    normalized = value.strip()
    if len(normalized) > max_length:
        raise ValueError(f"{field} has an invalid length.")
    return normalized or None


def normalize_asset_name(name: str) -> str:
    return _normalize_required_text(
        name, field="Asset name", max_length=ASSET_NAME_MAX_LENGTH
    )


def normalize_asset_tag(asset_tag: str) -> str:
    if not isinstance(asset_tag, str):
        raise ValueError("Asset tag must be a string.")
    normalized = asset_tag.strip().upper()
    if not normalized or len(normalized) > ASSET_TAG_MAX_LENGTH:
        raise ValueError("Asset tag has an invalid length.")
    return normalized


def normalize_asset_optional_text(value: str | None, *, field: str) -> str | None:
    return _normalize_optional_text(
        value, field=field, max_length=ASSET_OPTIONAL_TEXT_MAX_LENGTH
    )


def normalize_asset_description(description: str | None) -> str | None:
    return _normalize_optional_text(
        description,
        field="Asset description",
        max_length=ASSET_DESCRIPTION_MAX_LENGTH,
    )


class Asset(db.Model):
    __tablename__ = "assets"
    __table_args__ = (
        db.UniqueConstraint("asset_tag", name="uq_assets_asset_tag"),
        db.CheckConstraint(
            "rack_unit_start >= 1", name="ck_assets_rack_unit_start_positive"
        ),
        db.CheckConstraint("rack_units >= 1", name="ck_assets_rack_units_positive"),
        db.CheckConstraint(
            "asset_type IN ('server', 'switch', 'router', 'firewall', 'storage', "
            "'appliance', 'access_point', 'notebook', 'desktop', 'other')",
            name="ck_assets_asset_type",
        ),
        db.CheckConstraint(
            "status IN ('active', 'inactive', 'maintenance')",
            name="ck_assets_status",
        ),
    )

    id = db.Column(db.Integer, primary_key=True)
    rack_id = db.Column(
        db.Integer,
        db.ForeignKey("racks.id", ondelete="RESTRICT"),
        nullable=False,
    )
    name = db.Column(db.String(ASSET_NAME_MAX_LENGTH), nullable=False)
    asset_tag = db.Column(db.String(ASSET_TAG_MAX_LENGTH), nullable=False)
    serial_number = db.Column(db.String(ASSET_OPTIONAL_TEXT_MAX_LENGTH), nullable=True)
    manufacturer = db.Column(db.String(ASSET_OPTIONAL_TEXT_MAX_LENGTH), nullable=True)
    model = db.Column(db.String(ASSET_OPTIONAL_TEXT_MAX_LENGTH), nullable=True)
    asset_type = db.Column(db.String(30), nullable=False)
    rack_unit_start = db.Column(db.Integer, nullable=False)
    rack_units = db.Column(db.Integer, nullable=False)
    description = db.Column(db.String(ASSET_DESCRIPTION_MAX_LENGTH), nullable=True)
    status = db.Column(
        db.String(20),
        nullable=False,
        default=AssetStatus.ACTIVE.value,
        server_default=AssetStatus.ACTIVE.value,
    )
    created_at = db.Column(db.DateTime(timezone=True), nullable=False, default=utc_now)
    updated_at = db.Column(
        db.DateTime(timezone=True), nullable=False, default=utc_now, onupdate=utc_now
    )

    rack = db.relationship("Rack", back_populates="assets")
    virtual_machines = db.relationship(
        "VirtualMachine",
        back_populates="host_asset",
        passive_deletes="all",
        order_by="VirtualMachine.name",
    )

    @validates("rack_id")
    def validate_rack_id(self, _key: str, rack_id: int) -> int:
        if not isinstance(rack_id, int) or isinstance(rack_id, bool) or rack_id <= 0:
            raise ValueError("Asset rack ID is invalid.")
        return rack_id

    @validates("name")
    def normalize_and_validate_name(self, _key: str, name: str) -> str:
        return normalize_asset_name(name)

    @validates("asset_tag")
    def normalize_and_validate_asset_tag(self, _key: str, asset_tag: str) -> str:
        return normalize_asset_tag(asset_tag)

    @validates("serial_number", "manufacturer", "model")
    def normalize_and_validate_optional_text(
        self, key: str, value: str | None
    ) -> str | None:
        return normalize_asset_optional_text(value, field=f"Asset {key}")

    @validates("asset_type")
    def validate_asset_type(self, _key: str, asset_type: str | AssetType) -> str:
        value = asset_type.value if isinstance(asset_type, AssetType) else asset_type
        if value not in VALID_ASSET_TYPES:
            raise ValueError("Asset type has an invalid value.")
        return value

    @validates("rack_unit_start", "rack_units")
    def validate_positive_rack_units(self, key: str, value: int) -> int:
        if not isinstance(value, int) or isinstance(value, bool) or value < 1:
            raise ValueError(f"Asset {key} must be a positive integer.")
        return value

    @validates("description")
    def normalize_and_validate_description(
        self, _key: str, description: str | None
    ) -> str | None:
        return normalize_asset_description(description)

    @validates("status")
    def validate_status(self, _key: str, status: str | AssetStatus) -> str:
        value = status.value if isinstance(status, AssetStatus) else status
        if value not in VALID_ASSET_STATUSES:
            raise ValueError("Asset status has an invalid value.")
        return value

    @property
    def type_label(self) -> str:
        return ASSET_TYPE_LABELS.get(self.asset_type, "Tipo inválido")

    @property
    def status_label(self) -> str:
        return ASSET_STATUS_LABELS.get(self.status, "Status inválido")

    @property
    def rack_unit_end(self) -> int:
        return self.rack_unit_start + self.rack_units - 1

    @property
    def rack_position_label(self) -> str:
        if self.rack_unit_start == self.rack_unit_end:
            return f"U{self.rack_unit_start}"
        return f"U{self.rack_unit_start}-U{self.rack_unit_end}"
