import json
from collections.abc import Mapping

from flask import current_app
from sqlalchemy.exc import SQLAlchemyError

from app.extensions import db
from app.models import AuditEventType, AuditLog, User, UserRole
from app.request_metadata import get_request_metadata


ALLOWED_DETAIL_KEYS = {
    AuditEventType.LOGIN_FAILURE: frozenset({"reason"}),
    AuditEventType.USER_CREATED: frozenset({"role", "is_active", "source"}),
    AuditEventType.USER_UPDATED: frozenset({"changed_fields"}),
    AuditEventType.USER_ROLE_CHANGED: frozenset({"old_role", "new_role"}),
    AuditEventType.DATACENTER_UPDATE: frozenset({"changed_fields"}),
    AuditEventType.ROOM_UPDATE: frozenset({"changed_fields"}),
    AuditEventType.RACK_UPDATE: frozenset({"changed_fields"}),
    AuditEventType.ASSET_UPDATE: frozenset({"changed_fields"}),
    AuditEventType.VM_UPDATE: frozenset({"changed_fields"}),
}
ALLOWED_CHANGED_FIELDS = {
    AuditEventType.USER_UPDATED: frozenset(
        {"username", "email", "is_active", "role"}
    ),
    AuditEventType.DATACENTER_UPDATE: frozenset(
        {"name", "code", "location", "description", "status"}
    ),
    AuditEventType.ROOM_UPDATE: frozenset(
        {"datacenter_id", "name", "code", "description", "status"}
    ),
    AuditEventType.RACK_UPDATE: frozenset(
        {"room_id", "name", "code", "capacity_u", "description", "status"}
    ),
    AuditEventType.ASSET_UPDATE: frozenset(
        {
            "rack_id",
            "name",
            "asset_tag",
            "serial_number",
            "manufacturer",
            "model",
            "asset_type",
            "rack_unit_start",
            "rack_units",
            "description",
            "status",
        }
    ),
    AuditEventType.VM_UPDATE: frozenset(
        {
            "host_asset_id",
            "name",
            "hostname",
            "ip_address",
            "operating_system",
            "vcpu",
            "memory_mb",
            "disk_gb",
            "environment",
            "status",
            "description",
        }
    ),
}
EVENT_RESOURCE_TYPES = {
    AuditEventType.DATACENTER_CREATE: "datacenter",
    AuditEventType.DATACENTER_UPDATE: "datacenter",
    AuditEventType.DATACENTER_DELETE: "datacenter",
    AuditEventType.ROOM_CREATE: "room",
    AuditEventType.ROOM_UPDATE: "room",
    AuditEventType.ROOM_DELETE: "room",
    AuditEventType.RACK_CREATE: "rack",
    AuditEventType.RACK_UPDATE: "rack",
    AuditEventType.RACK_DELETE: "rack",
    AuditEventType.ASSET_CREATE: "asset",
    AuditEventType.ASSET_UPDATE: "asset",
    AuditEventType.ASSET_DELETE: "asset",
    AuditEventType.VM_CREATE: "virtual_machine",
    AuditEventType.VM_UPDATE: "virtual_machine",
    AuditEventType.VM_DELETE: "virtual_machine",
    AuditEventType.SECURITY_ALERT_REVIEWED: "security_alert",
}
MAX_DETAILS_LENGTH = 1000
VALID_ROLES = frozenset(role.value for role in UserRole)


def record_event(
    event_type: AuditEventType,
    *,
    actor: User | None = None,
    target: User | None = None,
    details: Mapping[str, object] | None = None,
    resource_type: str | None = None,
    resource_id: int | None = None,
    result: str | None = None,
    commit: bool = True,
) -> AuditLog | None:
    if not isinstance(event_type, AuditEventType):
        raise ValueError("Audit event type must use AuditEventType.")

    safe_details = _sanitize_details(event_type, details or {})
    _validate_resource(event_type, resource_type, resource_id, result)
    metadata = get_request_metadata()

    audit_log = AuditLog(
        event_type=event_type,
        actor_user_id=actor.id if actor is not None else None,
        target_user_id=target.id if target is not None else None,
        ip_address=metadata.ip_address,
        user_agent=metadata.user_agent,
        details=safe_details,
        resource_type=resource_type,
        resource_id=resource_id,
        result=result,
    )
    if not commit:
        db.session.add(audit_log)
        return audit_log

    try:
        db.session.add(audit_log)
        db.session.commit()
    except SQLAlchemyError:
        db.session.rollback()
        current_app.logger.error(
            "Failed to persist audit event %s.", event_type.value
        )
        return None
    return audit_log


def _sanitize_details(
    event_type: AuditEventType, details: Mapping[str, object]
) -> dict[str, object]:
    allowed_keys = ALLOWED_DETAIL_KEYS.get(event_type, frozenset())
    unknown_keys = set(details) - allowed_keys
    if unknown_keys:
        raise ValueError("Audit details contain unsupported fields.")

    sanitized: dict[str, object] = {}
    for key, value in details.items():
        if key == "changed_fields":
            if not isinstance(value, (list, tuple, set)):
                raise ValueError("Audit changed fields must be a collection.")
            if not all(isinstance(field, str) for field in value):
                raise ValueError("Audit changed fields must contain strings.")
            changed_fields = sorted(set(value))
            allowed_changed_fields = ALLOWED_CHANGED_FIELDS.get(
                event_type, frozenset()
            )
            if not set(changed_fields) <= allowed_changed_fields:
                raise ValueError("Audit changed fields contain unsupported values.")
            sanitized[key] = changed_fields
        elif key == "is_active":
            if not isinstance(value, bool):
                raise ValueError("Audit status must be boolean.")
            sanitized[key] = value
        elif (
            key in {"role", "old_role", "new_role"}
            and isinstance(value, str)
            and value in VALID_ROLES
        ):
            sanitized[key] = value
        elif key == "source" and value == "cli":
            sanitized[key] = value
        elif key == "reason" and value == "authentication_failed":
            sanitized[key] = value
        else:
            raise ValueError("Audit detail value is invalid.")

    if len(json.dumps(sanitized, ensure_ascii=False)) > MAX_DETAILS_LENGTH:
        raise ValueError("Audit details are too long.")
    return sanitized


def _validate_resource(
    event_type: AuditEventType,
    resource_type: str | None,
    resource_id: int | None,
    result: str | None,
) -> None:
    expected_resource_type = EVENT_RESOURCE_TYPES.get(event_type)
    if expected_resource_type is None:
        if any(value is not None for value in (resource_type, resource_id, result)):
            raise ValueError("Audit resource is not supported for this event.")
        return

    if (
        resource_type != expected_resource_type
        or not isinstance(resource_id, int)
        or isinstance(resource_id, bool)
        or resource_id <= 0
        or result != "success"
    ):
        raise ValueError("Audit resource data is invalid.")


def format_details(details: Mapping[str, object]) -> str:
    if not details:
        return "-"

    labels = {
        "reason": "motivo",
        "role": "perfil",
        "is_active": "ativo",
        "source": "origem",
        "changed_fields": "campos alterados",
        "old_role": "perfil anterior",
        "new_role": "novo perfil",
    }
    parts = []
    for key, value in details.items():
        label = labels.get(key)
        if label is None:
            continue
        if isinstance(value, list):
            displayed_value = ", ".join(value)
        elif isinstance(value, bool):
            displayed_value = "sim" if value else "não"
        else:
            displayed_value = str(value)
        parts.append(f"{label}: {displayed_value}")
    return "; ".join(parts) or "-"
