from collections.abc import Iterator

import pytest
from flask import Flask
from flask.testing import FlaskClient

from app import create_app
from app.extensions import db
from app.models import User, UserRole


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
