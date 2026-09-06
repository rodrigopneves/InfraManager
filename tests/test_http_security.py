from urllib.parse import urlparse
from html.parser import HTMLParser

import pytest
from flask import Flask, abort
from flask.testing import FlaskClient

from app import create_app
from app.models import User
from config import ProductionConfig, TestingConfig
from tests.helpers import complete_login


EXPECTED_CSP_DIRECTIVES = {
    "default-src": {"'self'"},
    "script-src": {"'self'", "https://cdn.jsdelivr.net"},
    "script-src-attr": {"'none'"},
    "style-src": {"'self'", "https://cdn.jsdelivr.net"},
    "style-src-attr": {"'none'"},
    "img-src": {"'self'", "data:"},
    "object-src": {"'none'"},
    "base-uri": {"'self'"},
    "frame-ancestors": {"'none'"},
    "form-action": {"'self'"},
}


def parse_csp(value: str) -> dict[str, set[str]]:
    directives = {}
    for raw_directive in value.split(";"):
        name, *sources = raw_directive.strip().split()
        directives[name] = set(sources)
    return directives


def assert_security_headers(response) -> None:
    directives = parse_csp(response.headers["Content-Security-Policy"])
    for name, expected_sources in EXPECTED_CSP_DIRECTIVES.items():
        assert directives[name] == expected_sources
    assert "'unsafe-eval'" not in response.headers["Content-Security-Policy"]
    assert response.headers["X-Content-Type-Options"] == "nosniff"
    assert response.headers["X-Frame-Options"] == "DENY"
    assert response.headers["Referrer-Policy"] == "no-referrer"
    assert response.headers["Permissions-Policy"] == (
        "camera=(), geolocation=(), microphone=(), payment=(), usb=()"
    )
    assert response.headers["Cross-Origin-Opener-Policy"] == "same-origin"
    assert "Strict-Transport-Security" not in response.headers


def assert_no_store(response) -> None:
    assert response.headers["Cache-Control"] == "no-store"
    assert response.headers["Pragma"] == "no-cache"
    assert response.headers["Expires"] == "0"


def test_public_page_has_security_headers_without_sensitive_cache_policy(
    client: FlaskClient,
) -> None:
    response = client.get("/")

    assert response.status_code == 200
    assert_security_headers(response)
    assert "no-store" not in response.headers.get("Cache-Control", "")
    assert "Pragma" not in response.headers
    assert "Expires" not in response.headers


def test_static_asset_keeps_normal_cache_behavior(
    client: FlaskClient, viewer_user: User
) -> None:
    complete_login(client, viewer_user.username, "valid-viewer-password")
    response = client.get("/static/css/app.css")

    assert response.status_code == 200
    assert_security_headers(response)
    assert "no-store" not in response.headers.get("Cache-Control", "")
    assert "Pragma" not in response.headers
    assert "Expires" not in response.headers


def test_authenticated_dashboard_and_admin_pages_are_not_stored(
    client: FlaskClient, admin_user: User
) -> None:
    complete_login(client, admin_user.username, "valid-admin-password")

    for path in (
        "/dashboard", "/admin/users", "/admin/audit", "/datacenters",
        "/rooms", "/racks", "/assets", "/virtual-machines",
        "/account/mfa/disable",
    ):
        response = client.get(path)
        assert response.status_code == 200
        assert_security_headers(response)
        assert_no_store(response)


def test_public_login_with_session_bound_csrf_is_not_stored() -> None:
    app = create_app(TestingConfig)
    app.config["WTF_CSRF_ENABLED"] = True
    first_client = app.test_client()
    second_client = app.test_client()

    class CsrfParser(HTMLParser):
        token = None

        def handle_starttag(self, tag, attrs):
            attributes = dict(attrs)
            if tag == "input" and attributes.get("name") == "csrf_token":
                self.token = attributes.get("value")

    first_response = first_client.get("/login")
    second_response = second_client.get("/login")
    first_form = CsrfParser()
    first_form.feed(first_response.get_data(as_text=True))
    second_form = CsrfParser()
    second_form.feed(second_response.get_data(as_text=True))
    assert first_form.token and second_form.token
    assert first_form.token != second_form.token
    assert_no_store(first_response)
    assert_no_store(second_response)
    # A token cached for a different session must not authorize a login POST.
    rejected = second_client.post("/login", data={"csrf_token": first_form.token})
    assert rejected.status_code == 400
    assert_no_store(rejected)


def test_mfa_pages_and_redirects_are_not_stored(
    client: FlaskClient, user_without_mfa: User, mfa_user: User
) -> None:
    login_response = client.post(
        "/login",
        data={
            "username": user_without_mfa.username,
            "password": "valid-setup-password",
        },
    )
    setup_response = client.get("/account/mfa/setup")

    assert urlparse(login_response.location).path == "/account/mfa/setup"
    for response in (login_response, setup_response):
        assert_security_headers(response)
        assert_no_store(response)

    client.post("/account/mfa/setup/cancel")
    client.post(
        "/login",
        data={"username": mfa_user.username, "password": "valid-mfa-password"},
    )
    verify_response = client.get("/mfa/verify")
    assert verify_response.status_code == 200
    assert_security_headers(verify_response)
    assert_no_store(verify_response)


@pytest.mark.parametrize("status_code", [400, 403, 404, 413, 429, 500])
def test_error_responses_receive_security_headers(
    app: Flask, status_code: int, admin_user: User
) -> None:
    endpoint = f"test_error_{status_code}"
    app.add_url_rule(
        f"/_test/error/{status_code}",
        endpoint,
        lambda code=status_code: abort(code),
    )
    client = app.test_client()

    response = client.get(f"/_test/error/{status_code}")

    assert response.status_code == status_code
    assert_security_headers(response)
    assert b"Traceback" not in response.data
    assert b"/home/" not in response.data

    complete_login(client, admin_user.username, "valid-admin-password")
    authenticated_response = client.get(f"/_test/error/{status_code}")
    assert authenticated_response.status_code == status_code
    assert_security_headers(authenticated_response)
    assert_no_store(authenticated_response)


def test_hsts_is_reserved_for_tls_terminator_in_testing(
    client: FlaskClient,
) -> None:
    assert "Strict-Transport-Security" not in client.get("/").headers
    assert "Strict-Transport-Security" not in client.get(
        "/", base_url="https://localhost"
    ).headers


def test_hsts_is_reserved_for_tls_terminator_in_development() -> None:
    app = create_app("development")
    response = app.test_client().get("/", base_url="https://localhost")

    assert response.status_code == 200
    assert_security_headers(response)


def test_hsts_is_not_duplicated_by_flask_in_production() -> None:
    class HeaderProductionConfig(ProductionConfig):
        SECRET_KEY = "production-header-test-only-secret"
        SQLALCHEMY_DATABASE_URI = "sqlite:///:memory:"
        MFA_ENCRYPTION_KEY = TestingConfig.MFA_ENCRYPTION_KEY
        RATELIMIT_ENABLED = False
        RATELIMIT_STORAGE_URI = "redis://rate-limit.example.invalid:6379/0"

    app = create_app(HeaderProductionConfig)
    response = app.test_client().get("/", base_url="https://192.0.2.10")

    assert response.status_code == 200
    assert_security_headers(response)
