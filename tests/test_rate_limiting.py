from collections.abc import Iterator

import pytest
import pyotp
from flask import Flask
from flask.testing import FlaskClient

from app import create_app
from app.extensions import db, limiter
from app.models import User
from config import TestingConfig


class RateLimitTestingConfig(TestingConfig):
    RATELIMIT_ENABLED = True
    RATELIMIT_STORAGE_URI = "memory://"


@pytest.fixture()
def rate_limited_app() -> Iterator[Flask]:
    application = create_app(RateLimitTestingConfig)

    with application.app_context():
        db.create_all()
        limiter.reset()
        yield application
        limiter.reset()
        db.session.remove()
        db.drop_all()


@pytest.fixture()
def rate_limited_client(rate_limited_app: Flask) -> FlaskClient:
    return rate_limited_app.test_client()


def post_login(
    client: FlaskClient,
    *,
    remote_address: str = "192.0.2.10",
    username: str = "unknown.demo",
    password: str = "sensitive-test-password",
):
    return client.post(
        "/login",
        data={"username": username, "password": password},
        environ_overrides={"REMOTE_ADDR": remote_address},
    )


def exceed_login_limit(client: FlaskClient, remote_address: str) -> None:
    for _ in range(5):
        assert post_login(client, remote_address=remote_address).status_code == 200


def test_login_attempts_below_limit_are_processed(
    rate_limited_client: FlaskClient,
) -> None:
    for _ in range(5):
        response = post_login(rate_limited_client)
        assert response.status_code == 200


def test_exceeding_login_limit_returns_safe_429_response(
    rate_limited_client: FlaskClient,
) -> None:
    exceed_login_limit(rate_limited_client, "192.0.2.20")

    response = post_login(rate_limited_client, remote_address="192.0.2.20")

    assert response.status_code == 429
    assert (
        "Muitas tentativas foram realizadas. "
        "Aguarde alguns minutos e tente novamente."
    ).encode() in response.data
    response_content = response.data.lower()
    assert b"unknown.demo" not in response_content
    assert b"sensitive-test-password" not in response_content
    assert b"flask-limiter" not in response_content
    assert b"5 per 15" not in response_content


def test_get_login_and_health_remain_available_after_limit(
    rate_limited_client: FlaskClient,
) -> None:
    exceed_login_limit(rate_limited_client, "192.0.2.30")
    assert (
        post_login(rate_limited_client, remote_address="192.0.2.30").status_code
        == 429
    )

    login_response = rate_limited_client.get(
        "/login", environ_overrides={"REMOTE_ADDR": "192.0.2.30"}
    )
    health_response = rate_limited_client.get(
        "/health", environ_overrides={"REMOTE_ADDR": "192.0.2.30"}
    )

    assert login_response.status_code == 200
    assert health_response.status_code == 200
    assert health_response.get_json() == {"status": "ok"}


def test_valid_login_works_before_limit(
    rate_limited_client: FlaskClient, rate_limited_app: Flask
) -> None:
    user = User(username="limited.demo", email="limited.demo@example.com")
    user.set_password("valid-test-password")
    db.session.add(user)
    db.session.commit()

    response = post_login(
        rate_limited_client,
        remote_address="198.51.100.10",
        username="limited.demo",
        password="valid-test-password",
    )

    assert response.status_code == 302
    assert response.location.endswith("/account/mfa/setup")
    assert rate_limited_client.get("/dashboard").status_code == 302


def test_different_remote_addresses_have_independent_limits(
    rate_limited_client: FlaskClient,
) -> None:
    exceed_login_limit(rate_limited_client, "203.0.113.10")
    assert (
        post_login(rate_limited_client, remote_address="203.0.113.10").status_code
        == 429
    )

    independent_response = post_login(
        rate_limited_client, remote_address="203.0.113.11"
    )

    assert independent_response.status_code == 200


def test_mfa_verification_has_a_dedicated_rate_limit(
    rate_limited_client: FlaskClient, rate_limited_app: Flask
) -> None:
    user = User(
        username="limited.mfa",
        email="limited.mfa@example.com",
        mfa_enabled=True,
        mfa_secret=pyotp.random_base32(),
    )
    user.set_password("valid-mfa-password")
    db.session.add(user)
    db.session.commit()
    remote_address = "198.51.100.20"
    login_response = post_login(
        rate_limited_client,
        remote_address=remote_address,
        username=user.username,
        password="valid-mfa-password",
    )
    assert login_response.status_code == 302
    assert login_response.location.endswith("/mfa/verify")
    current_code = pyotp.TOTP(user.mfa_secret).now()
    invalid_code = "000000" if current_code != "000000" else "000001"

    for _ in range(5):
        response = rate_limited_client.post(
            "/mfa/verify",
            data={"code": invalid_code},
            environ_overrides={"REMOTE_ADDR": remote_address},
        )
        assert response.status_code == 200

    blocked_response = rate_limited_client.post(
        "/mfa/verify",
        data={"code": invalid_code},
        environ_overrides={"REMOTE_ADDR": remote_address},
    )
    assert blocked_response.status_code == 429
    assert invalid_code.encode() not in blocked_response.data


def test_mfa_setup_has_a_dedicated_rate_limit(
    rate_limited_client: FlaskClient, rate_limited_app: Flask
) -> None:
    user = User(username="setup.limit", email="setup.limit@example.com")
    user.set_password("valid-test-password")
    db.session.add(user)
    db.session.commit()
    remote_address = "198.51.100.30"
    post_login(
        rate_limited_client,
        remote_address=remote_address,
        username=user.username,
        password="valid-test-password",
    )
    rate_limited_client.get(
        "/account/mfa/setup",
        environ_overrides={"REMOTE_ADDR": remote_address},
    )

    for _ in range(5):
        response = rate_limited_client.post(
            "/account/mfa/setup",
            data={"code": "000000"},
            environ_overrides={"REMOTE_ADDR": remote_address},
        )
        assert response.status_code == 200

    blocked_response = rate_limited_client.post(
        "/account/mfa/setup",
        data={"code": "000000"},
        environ_overrides={"REMOTE_ADDR": remote_address},
    )
    assert blocked_response.status_code == 429


def test_mfa_disable_has_a_dedicated_rate_limit(
    rate_limited_client: FlaskClient, rate_limited_app: Flask
) -> None:
    user = User(
        username="disable.limit",
        email="disable.limit@example.com",
        mfa_enabled=True,
        mfa_secret=pyotp.random_base32(),
    )
    user.set_password("valid-mfa-password")
    db.session.add(user)
    db.session.commit()
    remote_address = "198.51.100.40"
    post_login(
        rate_limited_client,
        remote_address=remote_address,
        username=user.username,
        password="valid-mfa-password",
    )
    rate_limited_client.post(
        "/mfa/verify",
        data={"code": pyotp.TOTP(user.mfa_secret).now()},
        environ_overrides={"REMOTE_ADDR": remote_address},
    )

    for _ in range(5):
        response = rate_limited_client.post(
            "/account/mfa/disable",
            data={"password": "wrong-password", "code": "000000"},
            environ_overrides={"REMOTE_ADDR": remote_address},
        )
        assert response.status_code == 200

    blocked_response = rate_limited_client.post(
        "/account/mfa/disable",
        data={"password": "wrong-password", "code": "000000"},
        environ_overrides={"REMOTE_ADDR": remote_address},
    )
    assert blocked_response.status_code == 429
