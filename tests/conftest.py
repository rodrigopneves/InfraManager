from collections.abc import Iterator

import pytest
import pyotp
from flask import Flask
from flask.testing import FlaskClient

from app import create_app
from app.extensions import db
from app.models import (
    Asset,
    AssetType,
    Datacenter,
    Rack,
    Room,
    User,
    UserRole,
    VirtualMachine,
)


@pytest.fixture()
def app() -> Iterator[Flask]:
    application = create_app("testing")

    with application.app_context():
        db.create_all()
        yield application
        db.session.remove()
        db.drop_all()


@pytest.fixture()
def client(app: Flask) -> FlaskClient:
    return app.test_client()


@pytest.fixture()
def active_user(app: Flask) -> User:
    user = User(username="login.demo", email="login.demo@example.com")
    user.set_password("valid-test-password")
    db.session.add(user)
    db.session.commit()
    return user


@pytest.fixture()
def admin_user(app: Flask) -> User:
    user = User(
        username="admin.demo",
        email="admin.demo@example.com",
        role=UserRole.ADMIN.value,
    )
    user.set_password("valid-admin-password")
    db.session.add(user)
    db.session.commit()
    return user


@pytest.fixture()
def regular_user(app: Flask) -> User:
    user = User(username="user.demo", email="user.demo@example.com")
    user.set_password("valid-user-password")
    db.session.add(user)
    db.session.commit()
    return user


@pytest.fixture()
def operator_user(app: Flask) -> User:
    user = User(
        username="operator.demo",
        email="operator.demo@example.com",
        role=UserRole.OPERATOR.value,
    )
    user.set_password("valid-operator-password")
    db.session.add(user)
    db.session.commit()
    return user


@pytest.fixture()
def viewer_user(app: Flask) -> User:
    user = User(
        username="viewer.demo",
        email="viewer.demo@example.com",
        role=UserRole.VIEWER.value,
    )
    user.set_password("valid-viewer-password")
    db.session.add(user)
    db.session.commit()
    return user


@pytest.fixture()
def mfa_user(app: Flask) -> User:
    user = User(
        username="mfa.demo",
        email="mfa.demo@example.com",
        mfa_enabled=True,
        mfa_secret=pyotp.random_base32(),
    )
    user.set_password("valid-mfa-password")
    db.session.add(user)
    db.session.commit()
    return user


@pytest.fixture()
def sample_datacenter(app: Flask) -> Datacenter:
    datacenter = Datacenter(
        name="Datacenter Laboratório",
        code="DC-LAB-01",
        location="São Paulo",
        description="Ambiente fictício para testes.",
    )
    db.session.add(datacenter)
    db.session.commit()
    return datacenter


@pytest.fixture()
def sample_room(app: Flask, sample_datacenter: Datacenter) -> Room:
    room = Room(
        datacenter_id=sample_datacenter.id,
        name="Sala Laboratório",
        code="ROOM-LAB-01",
        description="Sala fictícia para testes.",
    )
    db.session.add(room)
    db.session.commit()
    return room


@pytest.fixture()
def sample_rack(app: Flask, sample_room: Room) -> Rack:
    rack = Rack(
        room_id=sample_room.id,
        name="Rack Laboratório",
        code="RACK-LAB-01",
        capacity_u=42,
        description="Rack fictício para testes.",
    )
    db.session.add(rack)
    db.session.commit()
    return rack


@pytest.fixture()
def sample_asset(app: Flask, sample_rack: Rack) -> Asset:
    asset = Asset(
        rack_id=sample_rack.id,
        name="Servidor Laboratório",
        asset_tag="SRV-LAB-01",
        serial_number="SN-DEMO-001",
        manufacturer="Fabricante Demo",
        model="Modelo Demo",
        asset_type=AssetType.SERVER.value,
        rack_unit_start=10,
        rack_units=2,
        description="Ativo fictício para testes.",
    )
    db.session.add(asset)
    db.session.commit()
    return asset


@pytest.fixture()
def sample_virtual_machine(
    app: Flask, sample_asset: Asset
) -> VirtualMachine:
    virtual_machine = VirtualMachine(
        host_asset_id=sample_asset.id,
        name="VM-LAB-01",
        hostname="vm-lab-01.example.test",
        ip_address="192.0.2.10",
        operating_system="Ubuntu Server 24.04",
        vcpu=2,
        memory_mb=4096,
        disk_gb=80,
        environment="test",
        description="VM fictícia para testes.",
    )
    db.session.add(virtual_machine)
    db.session.commit()
    return virtual_machine
