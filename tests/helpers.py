import time
from urllib.parse import urlparse

import pyotp
from flask import Flask
from flask.testing import FlaskClient

from app.extensions import db
from app.models import User


def dispose_database(application: Flask) -> None:
    with application.app_context():
        db.session.remove()
        db.engine.dispose()


def valid_unused_totp(user: User) -> str:
    current_step = int(time.time()) // pyotp.TOTP(user.mfa_secret).interval
    minimum_step = user.mfa_last_used_step or -1
    for step in (current_step, current_step + 1, current_step - 1):
        if step > minimum_step:
            return pyotp.TOTP(user.mfa_secret).at(step * 30)
    raise AssertionError("No unused TOTP is available inside the accepted window.")


def complete_login(
    client: FlaskClient,
    username: str,
    password: str,
    *,
    environ_overrides: dict | None = None,
    headers: dict | None = None,
):
    request_options = {}
    if environ_overrides is not None:
        request_options["environ_overrides"] = environ_overrides
    if headers is not None:
        request_options["headers"] = headers

    first_factor = client.post(
        "/login",
        data={"username": username, "password": password},
        **request_options,
    )
    assert first_factor.status_code == 302
    assert urlparse(first_factor.location).path == "/mfa/verify"

    user = db.session.scalar(db.select(User).where(User.username == username))
    assert user is not None
    second_factor = client.post(
        "/mfa/verify",
        data={"code": valid_unused_totp(user)},
        **request_options,
    )
    assert second_factor.status_code == 302
    assert urlparse(second_factor.location).path == "/dashboard"
    return second_factor
