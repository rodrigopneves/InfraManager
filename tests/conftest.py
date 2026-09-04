from collections.abc import Iterator

import pytest
import pyotp
from flask import Flask
from flask.testing import FlaskClient

from app import create_app
from app.extensions import db
from app.models import Datacenter, Room, User, UserRole


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
