import logging
from datetime import timedelta

from flask import current_app
from sqlalchemy.exc import SQLAlchemyError

from app.extensions import db
from app.models import (
    SecurityAlert,
    SecurityAlertSeverity,
    SecurityAlertStatus,
    SecurityAlertType,
    User,
)
from app.models.security_alert import utc_now
from app.request_metadata import get_request_metadata


LOG_LEVELS = {
    SecurityAlertSeverity.WARNING: logging.WARNING,
    SecurityAlertSeverity.ERROR: logging.ERROR,
    SecurityAlertSeverity.CRITICAL: logging.CRITICAL,
}


def record_security_event(
    event_type: SecurityAlertType,
    severity: SecurityAlertSeverity,
    *,
    user: User | None = None,
    user_id: int | None = None,
    emit_log: bool = True,
) -> SecurityAlert | None:
    if not isinstance(event_type, SecurityAlertType):
        raise ValueError("Security event type must use SecurityAlertType.")
    if not isinstance(severity, SecurityAlertSeverity):
        raise ValueError("Security severity must use SecurityAlertSeverity.")
    if user is not None and user_id is not None:
        raise ValueError("Provide either user or user_id, not both.")

    related_user_id = user.id if user is not None else user_id
    metadata = get_request_metadata()
    now = utc_now()
    window_minutes = current_app.config["SECURITY_ALERT_WINDOW_MINUTES"]
    cutoff = now - timedelta(minutes=window_minutes)

    try:
        query = db.select(SecurityAlert).where(
            SecurityAlert.event_type == event_type.value,
            SecurityAlert.severity == severity.value,
            SecurityAlert.status == SecurityAlertStatus.NEW.value,
            SecurityAlert.ip_address == metadata.ip_address,
            SecurityAlert.user_id == related_user_id,
            SecurityAlert.endpoint == metadata.endpoint,
            SecurityAlert.last_seen_at >= cutoff,
        ).order_by(SecurityAlert.last_seen_at.desc(), SecurityAlert.id.desc())
        alert = db.session.scalar(query)
        if alert is None:
            alert = SecurityAlert(
                event_type=event_type,
                severity=severity,
                user_id=related_user_id,
                ip_address=metadata.ip_address,
                user_agent=metadata.user_agent,
                endpoint=metadata.endpoint,
                first_seen_at=now,
                last_seen_at=now,
            )
            db.session.add(alert)
        else:
            alert.occurrence_count += 1
            alert.last_seen_at = now
            alert.user_agent = metadata.user_agent
        db.session.commit()
    except SQLAlchemyError:
        db.session.rollback()
        current_app.logger.error(
            "security_alert_persistence_failed event_type=%s", event_type.value
        )
        return None

    if emit_log:
        current_app.logger.log(
            LOG_LEVELS[severity],
            "security_event=%s user_id=%s ip_address=%s endpoint=%s occurrences=%s",
            event_type.value,
            related_user_id if related_user_id is not None else "-",
            metadata.ip_address or "-",
            metadata.endpoint or "-",
            alert.occurrence_count,
        )
    return alert
