from datetime import datetime, timezone
from enum import Enum
from ipaddress import ip_address

from sqlalchemy.orm import validates

from app.extensions import db


VIRTUAL_MACHINE_NAME_MAX_LENGTH = 120
VIRTUAL_MACHINE_HOSTNAME_MAX_LENGTH = 253
VIRTUAL_MACHINE_IP_MAX_LENGTH = 45
VIRTUAL_MACHINE_OS_MAX_LENGTH = 120
VIRTUAL_MACHINE_DESCRIPTION_MAX_LENGTH = 1000
VIRTUAL_MACHINE_VCPU_MIN = 1
VIRTUAL_MACHINE_VCPU_MAX = 512
VIRTUAL_MACHINE_MEMORY_MB_MIN = 128
VIRTUAL_MACHINE_MEMORY_MB_MAX = 4_194_304
VIRTUAL_MACHINE_DISK_GB_MIN = 1
VIRTUAL_MACHINE_DISK_GB_MAX = 1_048_576


class VirtualMachineEnvironment(str, Enum):
    PRODUCTION = "production"
    STAGING = "staging"
    DEVELOPMENT = "development"
    TEST = "test"
    OTHER = "other"


VIRTUAL_MACHINE_ENVIRONMENT_LABELS = {
    VirtualMachineEnvironment.PRODUCTION.value: "Produção",
    VirtualMachineEnvironment.STAGING.value: "Homologação",
    VirtualMachineEnvironment.DEVELOPMENT.value: "Desenvolvimento",
    VirtualMachineEnvironment.TEST.value: "Teste",
    VirtualMachineEnvironment.OTHER.value: "Outro",
}
VIRTUAL_MACHINE_ENVIRONMENT_CHOICES = tuple(
    (environment.value, VIRTUAL_MACHINE_ENVIRONMENT_LABELS[environment.value])
    for environment in VirtualMachineEnvironment
)
VALID_VIRTUAL_MACHINE_ENVIRONMENTS = frozenset(
    environment.value for environment in VirtualMachineEnvironment
)


class VirtualMachineStatus(str, Enum):
    RUNNING = "running"
    STOPPED = "stopped"
    SUSPENDED = "suspended"
    MAINTENANCE = "maintenance"


VIRTUAL_MACHINE_STATUS_LABELS = {
    VirtualMachineStatus.RUNNING.value: "Em execução",
    VirtualMachineStatus.STOPPED.value: "Desligada",
    VirtualMachineStatus.SUSPENDED.value: "Suspensa",
    VirtualMachineStatus.MAINTENANCE.value: "Manutenção",
}
VIRTUAL_MACHINE_STATUS_CHOICES = tuple(
    (status.value, VIRTUAL_MACHINE_STATUS_LABELS[status.value])
    for status in VirtualMachineStatus
)
VALID_VIRTUAL_MACHINE_STATUSES = frozenset(
    status.value for status in VirtualMachineStatus
)


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


def normalize_virtual_machine_name(name: str) -> str:
    return _normalize_required_text(
        name,
        field="Virtual machine name",
        max_length=VIRTUAL_MACHINE_NAME_MAX_LENGTH,
    )


def normalize_virtual_machine_hostname(hostname: str | None) -> str | None:
    return _normalize_optional_text(
        hostname,
        field="Virtual machine hostname",
        max_length=VIRTUAL_MACHINE_HOSTNAME_MAX_LENGTH,
    )


def normalize_virtual_machine_ip_address(value: str | None) -> str | None:
    normalized = _normalize_optional_text(
        value,
        field="Virtual machine IP address",
        max_length=VIRTUAL_MACHINE_IP_MAX_LENGTH,
    )
    if normalized is None:
        return None
    try:
        return str(ip_address(normalized))
    except ValueError as error:
        raise ValueError("Virtual machine IP address is invalid.") from error


def normalize_virtual_machine_operating_system(value: str | None) -> str | None:
    return _normalize_optional_text(
        value,
        field="Virtual machine operating system",
        max_length=VIRTUAL_MACHINE_OS_MAX_LENGTH,
    )


def normalize_virtual_machine_description(value: str | None) -> str | None:
    return _normalize_optional_text(
        value,
        field="Virtual machine description",
        max_length=VIRTUAL_MACHINE_DESCRIPTION_MAX_LENGTH,
    )


class VirtualMachine(db.Model):
    __tablename__ = "virtual_machines"
    __table_args__ = (
        db.UniqueConstraint("name", name="uq_virtual_machines_name"),
        db.CheckConstraint(
            f"vcpu BETWEEN {VIRTUAL_MACHINE_VCPU_MIN} AND {VIRTUAL_MACHINE_VCPU_MAX}",
            name="ck_virtual_machines_vcpu",
        ),
        db.CheckConstraint(
            "memory_mb BETWEEN "
            f"{VIRTUAL_MACHINE_MEMORY_MB_MIN} AND {VIRTUAL_MACHINE_MEMORY_MB_MAX}",
            name="ck_virtual_machines_memory_mb",
        ),
        db.CheckConstraint(
            "disk_gb BETWEEN "
            f"{VIRTUAL_MACHINE_DISK_GB_MIN} AND {VIRTUAL_MACHINE_DISK_GB_MAX}",
            name="ck_virtual_machines_disk_gb",
        ),
        db.CheckConstraint(
            "environment IN ('production', 'staging', 'development', 'test', 'other')",
            name="ck_virtual_machines_environment",
        ),
        db.CheckConstraint(
            "status IN ('running', 'stopped', 'suspended', 'maintenance')",
            name="ck_virtual_machines_status",
        ),
    )

    id = db.Column(db.Integer, primary_key=True)
    host_asset_id = db.Column(
        db.Integer,
        db.ForeignKey("assets.id", ondelete="RESTRICT"),
        nullable=False,
    )
    name = db.Column(db.String(VIRTUAL_MACHINE_NAME_MAX_LENGTH), nullable=False)
    hostname = db.Column(db.String(VIRTUAL_MACHINE_HOSTNAME_MAX_LENGTH), nullable=True)
    ip_address = db.Column(db.String(VIRTUAL_MACHINE_IP_MAX_LENGTH), nullable=True)
    operating_system = db.Column(db.String(VIRTUAL_MACHINE_OS_MAX_LENGTH), nullable=True)
    vcpu = db.Column(db.Integer, nullable=False)
    memory_mb = db.Column(db.Integer, nullable=False)
    disk_gb = db.Column(db.Integer, nullable=False)
    environment = db.Column(db.String(20), nullable=False)
    status = db.Column(
        db.String(20),
        nullable=False,
        default=VirtualMachineStatus.STOPPED.value,
        server_default=VirtualMachineStatus.STOPPED.value,
    )
    description = db.Column(
        db.String(VIRTUAL_MACHINE_DESCRIPTION_MAX_LENGTH), nullable=True
    )
    created_at = db.Column(db.DateTime(timezone=True), nullable=False, default=utc_now)
    updated_at = db.Column(
        db.DateTime(timezone=True), nullable=False, default=utc_now, onupdate=utc_now
    )

    host_asset = db.relationship("Asset", back_populates="virtual_machines")

    @validates("host_asset_id")
    def validate_host_asset_id(self, _key: str, value: int) -> int:
        if not isinstance(value, int) or isinstance(value, bool) or value <= 0:
            raise ValueError("Virtual machine host asset ID is invalid.")
        return value

    @validates("name")
    def normalize_and_validate_name(self, _key: str, value: str) -> str:
        return normalize_virtual_machine_name(value)

    @validates("hostname")
    def normalize_and_validate_hostname(
        self, _key: str, value: str | None
    ) -> str | None:
        return normalize_virtual_machine_hostname(value)

    @validates("ip_address")
    def normalize_and_validate_ip_address(
        self, _key: str, value: str | None
    ) -> str | None:
        return normalize_virtual_machine_ip_address(value)

    @validates("operating_system")
    def normalize_and_validate_operating_system(
        self, _key: str, value: str | None
    ) -> str | None:
        return normalize_virtual_machine_operating_system(value)

    @validates("vcpu")
    def validate_vcpu(self, _key: str, value: int) -> int:
        return self._validate_integer_range(
            value, VIRTUAL_MACHINE_VCPU_MIN, VIRTUAL_MACHINE_VCPU_MAX, "vCPU"
        )

    @validates("memory_mb")
    def validate_memory_mb(self, _key: str, value: int) -> int:
        return self._validate_integer_range(
            value,
            VIRTUAL_MACHINE_MEMORY_MB_MIN,
            VIRTUAL_MACHINE_MEMORY_MB_MAX,
            "memory",
        )

    @validates("disk_gb")
    def validate_disk_gb(self, _key: str, value: int) -> int:
        return self._validate_integer_range(
            value,
            VIRTUAL_MACHINE_DISK_GB_MIN,
            VIRTUAL_MACHINE_DISK_GB_MAX,
            "disk",
        )

    @validates("environment")
    def validate_environment(
        self, _key: str, value: str | VirtualMachineEnvironment
    ) -> str:
        normalized = value.value if isinstance(value, VirtualMachineEnvironment) else value
        if normalized not in VALID_VIRTUAL_MACHINE_ENVIRONMENTS:
            raise ValueError("Virtual machine environment is invalid.")
        return normalized

    @validates("status")
    def validate_status(
        self, _key: str, value: str | VirtualMachineStatus
    ) -> str:
        normalized = value.value if isinstance(value, VirtualMachineStatus) else value
        if normalized not in VALID_VIRTUAL_MACHINE_STATUSES:
            raise ValueError("Virtual machine status is invalid.")
        return normalized

    @validates("description")
    def normalize_and_validate_description(
        self, _key: str, value: str | None
    ) -> str | None:
        return normalize_virtual_machine_description(value)

    @staticmethod
    def _validate_integer_range(
        value: int, minimum: int, maximum: int, field: str
    ) -> int:
        if (
            not isinstance(value, int)
            or isinstance(value, bool)
            or not minimum <= value <= maximum
        ):
            raise ValueError(f"Virtual machine {field} is outside the valid range.")
        return value

    @property
    def environment_label(self) -> str:
        return VIRTUAL_MACHINE_ENVIRONMENT_LABELS.get(
            self.environment, "Ambiente inválido"
        )

    @property
    def status_label(self) -> str:
        return VIRTUAL_MACHINE_STATUS_LABELS.get(self.status, "Status inválido")

    @property
    def memory_label(self) -> str:
        if self.memory_mb % 1024 == 0:
            return f"{self.memory_mb // 1024} GB"
        return f"{self.memory_mb} MB"
