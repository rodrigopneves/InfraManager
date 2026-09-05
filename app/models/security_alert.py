from datetime import datetime, timezone
from enum import Enum

from sqlalchemy.orm import validates

from app.extensions import db


class SecurityAlertType(str, Enum):
    LOGIN_FAILURE = "LOGIN_FAILURE"
    MFA_FAILURE = "MFA_FAILURE"
    RATE_LIMIT = "RATE_LIMIT"
    ADMIN_ACCESS_DENIED = "ADMIN_ACCESS_DENIED"
    INACTIVE_ACCOUNT = "INACTIVE_ACCOUNT"
    MFA_CONFIGURATION_FAILURE = "MFA_CONFIGURATION_FAILURE"
    MFA_DECRYPTION_FAILURE = "MFA_DECRYPTION_FAILURE"
    INTERNAL_AUTH_ERROR = "INTERNAL_AUTH_ERROR"


class SecurityAlertSeverity(str, Enum):
    WARNING = "WARNING"
    ERROR = "ERROR"
    CRITICAL = "CRITICAL"


class SecurityAlertStatus(str, Enum):
    NEW = "new"
    REVIEWED = "reviewed"


VALID_ALERT_TYPES = frozenset(value.value for value in SecurityAlertType)
VALID_ALERT_SEVERITIES = frozenset(value.value for value in SecurityAlertSeverity)
VALID_ALERT_STATUSES = frozenset(value.value for value in SecurityAlertStatus)


def utc_now() -> datetime:
    return datetime.now(timezone.utc)


class SecurityAlert(db.Model):
    __tablename__ = "security_alerts"
    __table_args__ = (
        db.CheckConstraint(
            "severity IN ('WARNING', 'ERROR', 'CRITICAL')",
            name="ck_security_alerts_severity",
        ),
        db.CheckConstraint(
            "status IN ('new', 'reviewed')",
            name="ck_security_alerts_status",
        ),
        db.CheckConstraint(
            "occurrence_count >= 1",
            name="ck_security_alerts_occurrence_count",
        ),
    )

    id = db.Column(db.Integer, primary_key=True)
    event_type = db.Column(db.String(50), nullable=False, index=True)
    severity = db.Column(db.String(10), nullable=False, index=True)
    status = db.Column(
        db.String(10),
        nullable=False,
        default=SecurityAlertStatus.NEW.value,
        server_default=SecurityAlertStatus.NEW.value,
        index=True,
    )
    user_id = db.Column(
        db.Integer,
        db.ForeignKey("users.id", ondelete="SET NULL"),
        nullable=True,
        index=True,
    )
    ip_address = db.Column(db.String(45), nullable=True)
    user_agent = db.Column(db.String(255), nullable=True)
    endpoint = db.Column(db.String(120), nullable=True)
    occurrence_count = db.Column(
        db.Integer, nullable=False, default=1, server_default="1"
    )
    first_seen_at = db.Column(
        db.DateTime(timezone=True), nullable=False, default=utc_now
    )
    last_seen_at = db.Column(
        db.DateTime(timezone=True), nullable=False, default=utc_now, index=True
    )
    reviewed_at = db.Column(db.DateTime(timezone=True), nullable=True)
    reviewed_by_user_id = db.Column(
        db.Integer,
        db.ForeignKey("users.id", ondelete="SET NULL"),
        nullable=True,
    )

    user = db.relationship("User", foreign_keys=[user_id])
    reviewed_by = db.relationship("User", foreign_keys=[reviewed_by_user_id])

    @validates("event_type")
    def validate_event_type(
        self, _key: str, event_type: str | SecurityAlertType
    ) -> str:
        value = (
            event_type.value
            if isinstance(event_type, SecurityAlertType)
            else event_type
        )
        if value not in VALID_ALERT_TYPES:
            raise ValueError("Security alert type is invalid.")
        return value

    @validates("severity")
    def validate_severity(
        self, _key: str, severity: str | SecurityAlertSeverity
    ) -> str:
        value = (
            severity.value
            if isinstance(severity, SecurityAlertSeverity)
            else severity
        )
        if value not in VALID_ALERT_SEVERITIES:
            raise ValueError("Security alert severity is invalid.")
        return value

    @validates("status")
    def validate_status(
        self, _key: str, status: str | SecurityAlertStatus
    ) -> str:
        value = (
            status.value if isinstance(status, SecurityAlertStatus) else status
        )
        if value not in VALID_ALERT_STATUSES:
            raise ValueError("Security alert status is invalid.")
        return value
