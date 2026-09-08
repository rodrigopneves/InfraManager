from ipaddress import ip_address

from flask import Flask
from sqlalchemy.exc import SQLAlchemyError

from app import create_app
from app.extensions import db
from app.models import (
    Asset,
    AssetStatus,
    AssetType,
    AuditLog,
    Datacenter,
    Rack,
    Room,
    User,
    VirtualMachine,
    VirtualMachineStatus,
)
from config import ProductionConfig, TestingConfig


EXPECTED_COUNTS = {
    Datacenter: 2,
    Room: 3,
    Rack: 5,
    Asset: 7,
    VirtualMachine: 7,
}


class SeedProductionConfig(ProductionConfig):
    SECRET_KEY = "seed-production-test-only-secret"
    SQLALCHEMY_DATABASE_URI = "sqlite:///:memory:"
    MFA_ENCRYPTION_KEY = TestingConfig.MFA_ENCRYPTION_KEY
    RATELIMIT_ENABLED = False
    RATELIMIT_STORAGE_URI = "redis://rate-limit.example.invalid:6379/0"


def count_records(model: type[db.Model]) -> int:
    return db.session.scalar(db.select(db.func.count()).select_from(model)) or 0


def run_seed(app: Flask):
    return app.test_cli_runner().invoke(args=["seed-demo"])


def test_seed_demo_command_is_available_in_development() -> None:
    app = create_app("development")

    result = app.test_cli_runner().invoke(args=["seed-demo", "--help"])

    assert result.exit_code == 0
    assert "Usage:" in result.output


def test_seed_demo_creates_expected_hierarchy_and_valid_demo_data(app: Flask) -> None:
    result = run_seed(app)

    assert result.exit_code == 0
    assert "24 criados, 0 já existentes" in result.output
    for model, expected_count in EXPECTED_COUNTS.items():
        assert count_records(model) == expected_count

    datacenters = {
        datacenter.code: datacenter
        for datacenter in db.session.scalars(db.select(Datacenter)).all()
    }
    assert datacenters["DC-MCZ-01"].name == "Datacenter Principal"
    assert datacenters["DC-MCZ-02"].name == "Datacenter Secundário"

    rooms = db.session.scalars(db.select(Room)).all()
    assert {(room.datacenter.code, room.code, room.name) for room in rooms} == {
        ("DC-MCZ-01", "PROD", "Sala Produção"),
        ("DC-MCZ-01", "HML", "Sala Homologação"),
        ("DC-MCZ-02", "DR", "Sala Disaster Recovery"),
    }

    racks = db.session.scalars(db.select(Rack)).all()
    assert {(rack.room.code, rack.code, rack.capacity_u) for rack in racks} == {
        ("PROD", "A01", 42),
        ("PROD", "A02", 42),
        ("PROD", "A03", 42),
        ("HML", "H01", 42),
        ("DR", "DR01", 44),
    }

    assets = db.session.scalars(db.select(Asset)).all()
    assert {asset.asset_tag for asset in assets} == {
        "SRV-PROD-01",
        "SRV-PROD-02",
        "STORAGE-01",
        "SW-CORE-01",
        "SW-CORE-02",
        "SRV-HML-01",
        "SRV-DR-01",
    }
    assert {asset.asset_type for asset in assets} >= {
        AssetType.SERVER.value,
        AssetType.STORAGE.value,
        AssetType.SWITCH.value,
    }
    assert {asset.status for asset in assets} == {
        AssetStatus.ACTIVE.value,
        AssetStatus.INACTIVE.value,
        AssetStatus.MAINTENANCE.value,
    }
    for rack in racks:
        rack_assets = sorted(rack.assets, key=lambda asset: asset.rack_unit_start)
        assert all(asset.rack_unit_end <= rack.capacity_u for asset in rack_assets)
        assert all(
            current.rack_unit_end < following.rack_unit_start
            for current, following in zip(rack_assets, rack_assets[1:])
        )

    virtual_machines = db.session.scalars(db.select(VirtualMachine)).all()
    assert {virtual_machine.name for virtual_machine in virtual_machines} == {
        "vm-web-01",
        "vm-web-02",
        "vm-db-01",
        "vm-monitoramento",
        "vm-homologacao",
        "vm-backup",
        "vm-ad-01",
    }
    assert all(
        virtual_machine.host_asset.asset_type == AssetType.SERVER.value
        for virtual_machine in virtual_machines
    )
    assert all(
        ip_address(virtual_machine.ip_address).is_private
        for virtual_machine in virtual_machines
    )
    assert {virtual_machine.status for virtual_machine in virtual_machines} >= {
        VirtualMachineStatus.RUNNING.value,
        VirtualMachineStatus.STOPPED.value,
        VirtualMachineStatus.MAINTENANCE.value,
    }


def test_seed_demo_is_idempotent_and_reports_existing_records(app: Flask) -> None:
    first_result = run_seed(app)
    first_counts = {model: count_records(model) for model in EXPECTED_COUNTS}

    second_result = run_seed(app)

    assert first_result.exit_code == 0
    assert second_result.exit_code == 0
    assert "0 criados, 24 já existentes" in second_result.output
    assert {model: count_records(model) for model in EXPECTED_COUNTS} == first_counts


def test_seed_demo_does_not_change_users_mfa_or_create_audit_events(
    app: Flask, active_user: User
) -> None:
    user_before = (
        active_user.username,
        active_user.email,
        active_user.password_hash,
        active_user._mfa_secret,
        active_user.mfa_enabled,
    )

    result = run_seed(app)
    db.session.refresh(active_user)

    assert result.exit_code == 0
    assert count_records(User) == 1
    assert (
        active_user.username,
        active_user.email,
        active_user.password_hash,
        active_user._mfa_secret,
        active_user.mfa_enabled,
    ) == user_before
    assert count_records(AuditLog) == 0


def test_seed_demo_rolls_back_everything_when_commit_fails(
    app: Flask, monkeypatch
) -> None:
    def fail_commit() -> None:
        raise SQLAlchemyError("simulated commit failure")

    monkeypatch.setattr(db.session, "commit", fail_commit)

    result = run_seed(app)

    assert result.exit_code == 1
    assert "Não foi possível popular os dados de demonstração." in result.output
    assert all(count_records(model) == 0 for model in EXPECTED_COUNTS)


def test_seed_demo_refuses_production_config() -> None:
    app = create_app(SeedProductionConfig)

    result = run_seed(app)

    assert result.exit_code == 1
    assert "seed-demo is not allowed in production." in result.output


def test_seed_demo_refuses_production_environment_variable(
    app: Flask, monkeypatch
) -> None:
    monkeypatch.setenv("FLASK_CONFIG", "production")

    result = run_seed(app)

    assert result.exit_code == 1
    assert "seed-demo is not allowed in production." in result.output
    assert all(count_records(model) == 0 for model in EXPECTED_COUNTS)
