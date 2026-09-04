from flask import Flask
from flask.testing import FlaskClient

from app.dashboard.services import (
    get_admin_dashboard_summary,
    get_dashboard_summary,
)
from app.extensions import db
from app.models import Asset, User, VirtualMachine, VirtualMachineStatus


def login(client: FlaskClient, user: User, password: str) -> None:
    response = client.post(
        "/login",
        data={"username": user.username, "password": password},
    )
    assert response.status_code == 302


def test_dashboard_summary_is_zero_with_empty_database(app: Flask) -> None:
    summary = get_dashboard_summary()

    assert summary.datacenters == 0
    assert summary.rooms == 0
    assert summary.racks == 0
    assert summary.assets == 0
    assert summary.virtual_machines == 0
    assert summary.rack_capacity_u == 0
    assert summary.rack_used_u == 0
    assert summary.rack_free_u == 0
    assert summary.rack_utilization_percentage == 0
    assert all(status.count == 0 for status in summary.asset_statuses)
    assert all(status.count == 0 for status in summary.virtual_machine_statuses)


def test_dashboard_summary_uses_real_infrastructure_data(
    app: Flask,
    sample_virtual_machine: VirtualMachine,
    sample_asset: Asset,
) -> None:
    sample_virtual_machine.status = VirtualMachineStatus.RUNNING.value
    db.session.commit()

    summary = get_dashboard_summary()
    asset_statuses = {status.value: status.count for status in summary.asset_statuses}
    vm_statuses = {
        status.value: status.count for status in summary.virtual_machine_statuses
    }

    assert summary.datacenters == 1
    assert summary.rooms == 1
    assert summary.racks == 1
    assert summary.assets == 1
    assert summary.virtual_machines == 1
    assert summary.rack_capacity_u == 42
    assert summary.rack_used_u == 2
    assert summary.rack_free_u == 40
    assert summary.rack_utilization_percentage == 5
    assert asset_statuses == {"active": 1, "inactive": 0, "maintenance": 0}
    assert vm_statuses == {
        "running": 1,
        "stopped": 0,
        "suspended": 0,
        "maintenance": 0,
    }


def test_dashboard_renders_real_counts_and_empty_states(
    client: FlaskClient,
    viewer_user: User,
    sample_virtual_machine: VirtualMachine,
) -> None:
    login(client, viewer_user, "valid-viewer-password")

    populated_response = client.get("/dashboard")

    assert populated_response.status_code == 200
    assert b'data-metric="datacenters" data-value="1"' in populated_response.data
    assert b'data-metric="rooms" data-value="1"' in populated_response.data
    assert b'data-metric="racks" data-value="1"' in populated_response.data
    assert b'data-metric="assets" data-value="1"' in populated_response.data
    assert (
        b'data-metric="virtual-machines" data-value="1"'
        in populated_response.data
    )
    assert b'value="2" max="42"' in populated_response.data


def test_dashboard_renders_empty_infrastructure_state(
    client: FlaskClient,
    viewer_user: User,
) -> None:
    login(client, viewer_user, "valid-viewer-password")

    response = client.get("/dashboard")

    assert response.status_code == 200
    assert b'data-metric="datacenters" data-value="0"' in response.data
    assert "Nenhum Ativo cadastrado.".encode() in response.data
    assert "Nenhuma Máquina Virtual cadastrada.".encode() in response.data
    assert "Nenhum Rack cadastrado.".encode() in response.data


def test_admin_summary_counts_users_and_recent_activity(
    client: FlaskClient,
    admin_user: User,
    operator_user: User,
    viewer_user: User,
) -> None:
    viewer_user.is_active = False
    db.session.commit()
    login(client, admin_user, "valid-admin-password")

    summary = get_admin_dashboard_summary()

    assert summary.active_users == 2
    assert summary.inactive_users == 1
    assert summary.administrators == 1
    assert summary.recent_activity
    assert summary.recent_activity[0].event_type == "LOGIN_SUCCESS"
    assert summary.recent_activity[0].actor_username == admin_user.username
    assert summary.recent_activity[0].resource == "Autenticação"


def test_admin_metrics_are_not_rendered_or_queried_for_viewer(
    client: FlaskClient,
    viewer_user: User,
    monkeypatch,
) -> None:
    def fail_if_called():
        raise AssertionError("Administrative summary must not be queried.")

    monkeypatch.setattr(
        "app.auth.routes.get_admin_dashboard_summary",
        fail_if_called,
    )
    login(client, viewer_user, "valid-viewer-password")

    response = client.get("/dashboard")

    assert response.status_code == 200
    assert b'id="admin-dashboard"' not in response.data
    assert b'data-admin-metric' not in response.data
    assert b"Atividade recente" not in response.data


def test_admin_dashboard_renders_restricted_metrics(
    client: FlaskClient,
    admin_user: User,
) -> None:
    login(client, admin_user, "valid-admin-password")

    response = client.get("/dashboard")

    assert response.status_code == 200
    assert b'id="admin-dashboard"' in response.data
    assert b'data-admin-metric="active-users" data-value="1"' in response.data
    assert b'data-admin-metric="inactive-users" data-value="0"' in response.data
    assert b'data-admin-metric="administrators" data-value="1"' in response.data
    assert b"LOGIN_SUCCESS" in response.data
