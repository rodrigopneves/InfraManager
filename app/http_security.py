from flask import Response, request
from flask_login import current_user


CONTENT_SECURITY_POLICY = "; ".join(
    (
        "default-src 'self'",
        "script-src 'self' https://cdn.jsdelivr.net",
        "script-src-attr 'none'",
        "style-src 'self' https://cdn.jsdelivr.net",
        "style-src-attr 'none'",
        "img-src 'self' data:",
        "font-src 'self'",
        "connect-src 'self'",
        "frame-src 'none'",
        "object-src 'none'",
        "base-uri 'self'",
        "frame-ancestors 'none'",
        "form-action 'self'",
    )
)
SENSITIVE_PUBLIC_BLUEPRINTS = frozenset({"auth", "account"})


def apply_http_security(response: Response) -> Response:
    response.headers["Content-Security-Policy"] = CONTENT_SECURITY_POLICY
    response.headers["X-Content-Type-Options"] = "nosniff"
    response.headers["X-Frame-Options"] = "DENY"
    response.headers["Referrer-Policy"] = "no-referrer"
    response.headers["Permissions-Policy"] = (
        "camera=(), geolocation=(), microphone=(), payment=(), usb=()"
    )
    response.headers["Cross-Origin-Opener-Policy"] = "same-origin"

    if request.endpoint != "static" and (
        current_user.is_authenticated
        or request.blueprint in SENSITIVE_PUBLIC_BLUEPRINTS
    ):
        response.headers["Cache-Control"] = "no-store"
        response.headers["Pragma"] = "no-cache"
        response.headers["Expires"] = "0"

    return response
