from datetime import datetime, timezone
from enum import Enum

from sqlalchemy.orm import validates

from app.extensions import db


class AuditEventType(str, Enum):
    LOGIN_SUCCESS = "LOGIN_SUCCESS"
    LOGIN_FAILURE = "LOGIN_FAILURE"
    LOGOUT = "LOGOUT"
    MFA_SUCCESS = "MFA_SUCCESS"
    MFA_FAILURE = "MFA_FAILURE"
    MFA_ENABLED = "MFA_ENABLED"
    MFA_DISABLED = "MFA_DISABLED"
    USER_CREATED = "USER_CREATED"
    USER_UPDATED = "USER_UPDATED"
    USER_ACTIVATED = "USER_ACTIVATED"
    USER_DEACTIVATED = "USER_DEACTIVATED"
    USER_ROLE_CHANGED = "USER_ROLE_CHANGED"
    DATACENTER_CREATE = "DATACENTER.CREATE"
    DATACENTER_UPDATE = "DATACENTER.UPDATE"
    DATACENTER_DELETE = "DATACENTER.DELETE"
    ROOM_CREATE = "ROOM.CREATE"
    ROOM_UPDATE = "ROOM.UPDATE"
    ROOM_DELETE = "ROOM.DELETE"
    RACK_CREATE = "RACK.CREATE"
    RACK_UPDATE = "RACK.UPDATE"
    RACK_DELETE = "RACK.DELETE"
    ASSET_CREATE = "ASSET.CREATE"
    ASSET_UPDATE = "ASSET.UPDATE"
    ASSET_DELETE = "ASSET.DELETE"
    VM_CREATE = "VM.CREATE"
    VM_UPDATE = "VM.UPDATE"
    VM_DELETE = "VM.DELETE"


VALID_AUDIT_EVENT_TYPES = frozenset(event.value for event in AuditEventType)


def utc_now() -> datetime:
    return datetime.now(timezone.utc)


class AuditLog(db.Model):
    __tablename__ = "audit_logs"

    id = db.Column(db.Integer, primary_key=True)
    event_type = db.Column(db.String(50), nullable=False, index=True)
    actor_user_id = db.Column(
        db.Integer,
        db.ForeignKey("users.id", ondelete="SET NULL"),
        nullable=True,
        index=True,
    )
    target_user_id = db.Column(
        db.Integer,
        db.ForeignKey("users.id", ondelete="SET NULL"),
        nullable=True,
        index=True,
    )
    ip_address = db.Column(db.String(45), nullable=True)
    user_agent = db.Column(db.String(255), nullable=True)
    details = db.Column(db.JSON, nullable=False, default=dict)
    resource_type = db.Column(db.String(50), nullable=True)
    resource_id = db.Column(db.Integer, nullable=True)
    result = db.Column(db.String(20), nullable=True)
    created_at = db.Column(
        db.DateTime(timezone=True), nullable=False, default=utc_now, index=True
    )

    actor = db.relationship("User", foreign_keys=[actor_user_id])
    target = db.relationship("User", foreign_keys=[target_user_id])

    @validates("event_type")
    def validate_event_type(
        self, _key: str, event_type: str | AuditEventType
    ) -> str:
        event_value = (
            event_type.value
            if isinstance(event_type, AuditEventType)
            else event_type
        )
        if event_value not in VALID_AUDIT_EVENT_TYPES:
            raise ValueError("Audit event type is invalid.")
        return event_value
