import json
from collections.abc import Mapping

from flask import current_app, has_request_context, request
from sqlalchemy.exc import SQLAlchemyError

from app.extensions import db
from app.models import AuditEventType, AuditLog, User, UserRole


ALLOWED_DETAIL_KEYS = {
    AuditEventType.LOGIN_FAILURE: frozenset({"reason"}),
    AuditEventType.USER_CREATED: frozenset({"role", "is_active", "source"}),
    AuditEventType.USER_UPDATED: frozenset({"changed_fields"}),
    AuditEventType.USER_ROLE_CHANGED: frozenset({"old_role", "new_role"}),
}
ALLOWED_CHANGED_FIELDS = frozenset({"username", "email", "is_active", "role"})
MAX_DETAILS_LENGTH = 1000
MAX_USER_AGENT_LENGTH = 255
VALID_ROLES = frozenset(role.value for role in UserRole)


def record_event(
    event_type: AuditEventType,
    *,
    actor: User | None = None,
    target: User | None = None,
    details: Mapping[str, object] | None = None,
) -> AuditLog | None:
    if not isinstance(event_type, AuditEventType):
        raise ValueError("Audit event type must use AuditEventType.")

    safe_details = _sanitize_details(event_type, details or {})
    ip_address = None
    user_agent = None
    if has_request_context():
        ip_address = (request.remote_addr or "")[:45] or None
        raw_user_agent = request.headers.get("User-Agent", "")
        user_agent = raw_user_agent[:MAX_USER_AGENT_LENGTH] or None

    audit_log = AuditLog(
        event_type=event_type,
        actor_user_id=actor.id if actor is not None else None,
        target_user_id=target.id if target is not None else None,
        ip_address=ip_address,
        user_agent=user_agent,
        details=safe_details,
    )
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
            if not set(changed_fields) <= ALLOWED_CHANGED_FIELDS:
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
