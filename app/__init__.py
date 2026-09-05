import logging
import os

from flask import Flask, render_template, request, session
from flask_login import current_user
from flask_wtf.csrf import CSRFError
from werkzeug.exceptions import (
    BadRequest,
    Forbidden,
    InternalServerError,
    NotFound,
    RequestEntityTooLarge,
    TooManyRequests,
)

import app.models  # noqa: F401 -- registers SQLAlchemy models before migrations
from app.extensions import csrf, db, limiter, login_manager, migrate
from app.http_security import apply_http_security
from app.mfa_crypto import MfaEncryptionError, validate_mfa_encryption_key
from config import CONFIGURATIONS, ProductionConfig


def create_app(config: str | object | None = None) -> Flask:
    app = Flask(__name__, instance_relative_config=True)
    selected_config = _resolve_config(config)
    app.config.from_object(selected_config)
    _configure_logging(app)

    if _uses_production_config(selected_config):
        _validate_production_config(app)

    db.init_app(app)
    migrate.init_app(app, db)
    login_manager.init_app(app)
    csrf.init_app(app)
    limiter.init_app(app)

    from app.auth import auth
    from app.account import account
    from app.admin import admin
    from app.datacenter import datacenter
    from app.room import room
    from app.rack import rack
    from app.asset import asset
    from app.virtual_machine import virtual_machine
    from app.commands import create_admin_command, encrypt_mfa_secrets_command
    from app.routes import main

    app.register_blueprint(account)
    app.register_blueprint(admin)
    app.register_blueprint(auth)
    app.register_blueprint(datacenter)
    app.register_blueprint(room)
    app.register_blueprint(rack)
    app.register_blueprint(asset)
    app.register_blueprint(virtual_machine)
    app.register_blueprint(main)
    app.cli.add_command(create_admin_command)
    app.cli.add_command(encrypt_mfa_secrets_command)
    app.register_error_handler(Forbidden, _handle_forbidden_error)
    app.register_error_handler(CSRFError, _handle_csrf_error)
    app.register_error_handler(TooManyRequests, _handle_rate_limit_error)
    app.register_error_handler(BadRequest, _handle_bad_request_error)
    app.register_error_handler(NotFound, _handle_not_found_error)
    app.register_error_handler(
        RequestEntityTooLarge, _handle_request_too_large_error
    )
    app.register_error_handler(
        InternalServerError, _handle_internal_server_error
    )
    app.after_request(apply_http_security)

    return app


def _validate_production_config(app: Flask) -> None:
    required_settings = {
        "DATABASE_URL": app.config.get("SQLALCHEMY_DATABASE_URI"),
        "MFA_ENCRYPTION_KEY": app.config.get("MFA_ENCRYPTION_KEY"),
        "SECRET_KEY": app.config.get("SECRET_KEY"),
    }
    missing_settings = [name for name, value in required_settings.items() if not value]
    if missing_settings:
        missing_names = ", ".join(missing_settings)
        app.logger.critical(
            "Production startup blocked by missing required configuration."
        )
        raise RuntimeError(
            f"Missing required production environment variables: {missing_names}."
        )
    try:
        validate_mfa_encryption_key(app.config["MFA_ENCRYPTION_KEY"])
    except MfaEncryptionError as error:
        app.logger.critical(
            "Production startup blocked by invalid MFA encryption configuration."
        )
        raise RuntimeError("MFA encryption configuration is invalid.") from error


def _handle_csrf_error(_error: CSRFError) -> tuple[str, int]:
    return render_template("errors/csrf.html"), 400


def _handle_rate_limit_error(_error: TooManyRequests) -> tuple[str, int]:
    from app.auth.services import PENDING_MFA_USER_ID_KEY
    from app.models import SecurityAlertSeverity, SecurityAlertType
    from app.security_alerts import record_security_event

    user_id = (
        int(current_user.get_id())
        if current_user.is_authenticated
        else session.get(PENDING_MFA_USER_ID_KEY)
    )
    record_security_event(
        SecurityAlertType.RATE_LIMIT,
        SecurityAlertSeverity.WARNING,
        user_id=user_id if isinstance(user_id, int) else None,
    )
    return render_template("errors/429.html"), 429


def _handle_forbidden_error(_error: Forbidden) -> tuple[str, int]:
    return render_template("errors/403.html"), 403


def _handle_bad_request_error(_error: BadRequest) -> tuple[str, int]:
    return render_template("errors/400.html"), 400


def _handle_not_found_error(_error: NotFound) -> tuple[str, int]:
    return render_template("errors/404.html"), 404


def _handle_request_too_large_error(
    _error: RequestEntityTooLarge,
) -> tuple[str, int]:
    return render_template("errors/413.html"), 413


def _handle_internal_server_error(
    error: InternalServerError,
) -> tuple[str, int]:
    from app.auth.services import PENDING_MFA_USER_ID_KEY
    from app.models import SecurityAlertSeverity, SecurityAlertType
    from app.security_alerts import record_security_event

    original_error = error.original_exception
    if isinstance(original_error, MfaEncryptionError):
        record_security_event(
            SecurityAlertType.MFA_DECRYPTION_FAILURE,
            SecurityAlertSeverity.ERROR,
            user_id=(
                session.get(PENDING_MFA_USER_ID_KEY)
                if isinstance(session.get(PENDING_MFA_USER_ID_KEY), int)
                else None
            ),
            emit_log=False,
        )
    elif original_error is not None and request.blueprint in {"auth", "account"}:
        record_security_event(
            SecurityAlertType.INTERNAL_AUTH_ERROR,
            SecurityAlertSeverity.ERROR,
            emit_log=False,
        )
    return render_template("errors/500.html"), 500


def _configure_logging(app: Flask) -> None:
    log_level = app.config.get("LOG_LEVEL", logging.INFO)
    logger = logging.getLogger(app.name)
    logger.setLevel(log_level)

    if not logger.hasHandlers():
        handler = logging.StreamHandler()
        handler.setFormatter(
            logging.Formatter("%(asctime)s %(levelname)s %(name)s: %(message)s")
        )
        logger.addHandler(handler)


def _resolve_config(config: str | object | None) -> object:
    if config is not None and not isinstance(config, str):
        return config

    config_name = config or os.getenv("FLASK_CONFIG", "development")

    try:
        return CONFIGURATIONS[config_name.lower()]
    except KeyError as error:
        valid_names = ", ".join(CONFIGURATIONS)
        raise ValueError(
            f"Unknown configuration '{config_name}'. Use one of: {valid_names}."
        ) from error


def _uses_production_config(config: object) -> bool:
    if isinstance(config, type):
        return issubclass(config, ProductionConfig)
    return isinstance(config, ProductionConfig)


def create_wsgi_app(config_name: str | None = None) -> Flask:
    selected_name = config_name or os.getenv("FLASK_CONFIG")
    if not selected_name:
        raise RuntimeError("FLASK_CONFIG must be set to 'production' for WSGI.")
    if selected_name.lower() != "production":
        raise RuntimeError(
            "The production WSGI entry point requires FLASK_CONFIG=production."
        )
    return create_app("production")
