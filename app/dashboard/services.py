from dataclasses import dataclass
from datetime import datetime

from sqlalchemy import func

from app.extensions import db
from app.models import (
    ASSET_STATUS_CHOICES,
    VIRTUAL_MACHINE_STATUS_CHOICES,
    Asset,
    AuditLog,
    Datacenter,
    Rack,
    Room,
    User,
    UserRole,
    VirtualMachine,
)


RECENT_ACTIVITY_LIMIT = 5


@dataclass(frozen=True)
class StatusMetric:
    value: str
    label: str
    count: int
    badge_class: str


@dataclass(frozen=True)
class DashboardSummary:
    datacenters: int
    rooms: int
    racks: int
    assets: int
    virtual_machines: int
    rack_capacity_u: int
    rack_used_u: int
    asset_statuses: tuple[StatusMetric, ...]
    virtual_machine_statuses: tuple[StatusMetric, ...]

    @property
    def rack_free_u(self) -> int:
        return max(self.rack_capacity_u - self.rack_used_u, 0)

    @property
    def rack_utilization_percentage(self) -> int:
        if self.rack_capacity_u == 0:
            return 0
        return round((self.rack_used_u / self.rack_capacity_u) * 100)


@dataclass(frozen=True)
class RecentActivity:
    event_type: str
    actor_username: str
    resource: str
    created_at: datetime


@dataclass(frozen=True)
class AdminDashboardSummary:
    active_users: int
    inactive_users: int
    administrators: int
    recent_activity: tuple[RecentActivity, ...]


def get_dashboard_summary() -> DashboardSummary:
    totals = db.session.execute(
        db.select(
            _count_subquery(Datacenter),
            _count_subquery(Room),
            _count_subquery(Rack),
            _count_subquery(Asset),
            _count_subquery(VirtualMachine),
            db.select(func.coalesce(func.sum(Rack.capacity_u), 0))
            .scalar_subquery(),
            db.select(func.coalesce(func.sum(Asset.rack_units), 0))
            .scalar_subquery(),
        )
    ).one()

    return DashboardSummary(
        datacenters=int(totals[0]),
        rooms=int(totals[1]),
        racks=int(totals[2]),
        assets=int(totals[3]),
        virtual_machines=int(totals[4]),
        rack_capacity_u=int(totals[5]),
        rack_used_u=int(totals[6]),
        asset_statuses=_status_metrics(
            Asset,
            Asset.status,
            ASSET_STATUS_CHOICES,
            {
                "active": "success",
                "inactive": "secondary",
                "maintenance": "warning",
            },
        ),
        virtual_machine_statuses=_status_metrics(
            VirtualMachine,
            VirtualMachine.status,
            VIRTUAL_MACHINE_STATUS_CHOICES,
            {
                "running": "success",
                "stopped": "secondary",
                "suspended": "info",
                "maintenance": "warning",
            },
        ),
    )


def get_admin_dashboard_summary() -> AdminDashboardSummary:
    user_counts = db.session.execute(
        db.select(
            func.count(User.id).filter(User.is_active.is_(True)),
            func.count(User.id).filter(User.is_active.is_(False)),
            func.count(User.id).filter(User.role == UserRole.ADMIN.value),
        )
    ).one()

    activity_rows = db.session.execute(
        db.select(
            AuditLog.event_type,
            AuditLog.resource_type,
            AuditLog.resource_id,
            AuditLog.created_at,
            User.username.label("actor_username"),
        )
        .outerjoin(User, AuditLog.actor_user_id == User.id)
        .order_by(AuditLog.created_at.desc(), AuditLog.id.desc())
        .limit(RECENT_ACTIVITY_LIMIT)
    ).all()

    return AdminDashboardSummary(
        active_users=int(user_counts[0]),
        inactive_users=int(user_counts[1]),
        administrators=int(user_counts[2]),
        recent_activity=tuple(
            RecentActivity(
                event_type=row.event_type,
                actor_username=row.actor_username or "Sistema",
                resource=_format_resource(row.resource_type, row.resource_id),
                created_at=row.created_at,
            )
            for row in activity_rows
        ),
    )


def _count_subquery(model):
    return db.select(func.count(model.id)).scalar_subquery()


def _status_metrics(
    model,
    status_column,
    choices: tuple[tuple[str, str], ...],
    badge_classes: dict[str, str],
) -> tuple[StatusMetric, ...]:
    rows = db.session.execute(
        db.select(status_column, func.count(model.id)).group_by(status_column)
    ).all()
    counts = {status: int(count) for status, count in rows}
    return tuple(
        StatusMetric(
            value=value,
            label=label,
            count=counts.get(value, 0),
            badge_class=badge_classes[value],
        )
        for value, label in choices
    )


def _format_resource(resource_type: str | None, resource_id: int | None) -> str:
    if resource_type is None or resource_id is None:
        return "Autenticação"

    resource_labels = {
        "datacenter": "Datacenter",
        "room": "Sala",
        "rack": "Rack",
        "asset": "Ativo",
        "virtual_machine": "Máquina Virtual",
    }
    label = resource_labels.get(resource_type, "Recurso")
    return f"{label} #{resource_id}"
