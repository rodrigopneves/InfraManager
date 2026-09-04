import logging
import os

from flask import Flask, render_template
from flask_wtf.csrf import CSRFError
from werkzeug.exceptions import Forbidden, TooManyRequests

import app.models
from app.extensions import csrf, db, limiter, login_manager, migrate
from config import CONFIGURATIONS, ProductionConfig


def create_app(config: str | object | None = None) -> Flask:
    app = Flask(__name__, instance_relative_config=True)
    selected_config = _resolve_config(config)
    app.config.from_object(selected_config)

    if selected_config is ProductionConfig:
        _validate_production_config(app)

    _configure_logging(app)
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
    from app.commands import create_admin_command
    from app.routes import main

    app.register_blueprint(account)
    app.register_blueprint(admin)
    app.register_blueprint(auth)
    app.register_blueprint(datacenter)
    app.register_blueprint(room)
    app.register_blueprint(rack)
    app.register_blueprint(main)
    app.cli.add_command(create_admin_command)
    app.register_error_handler(Forbidden, _handle_forbidden_error)
    app.register_error_handler(CSRFError, _handle_csrf_error)
    app.register_error_handler(TooManyRequests, _handle_rate_limit_error)

    return app


def _validate_production_config(app: Flask) -> None:
    required_settings = {
        "DATABASE_URL": app.config.get("SQLALCHEMY_DATABASE_URI"),
        "SECRET_KEY": app.config.get("SECRET_KEY"),
    }
    missing_settings = [name for name, value in required_settings.items() if not value]
    if missing_settings:
        missing_names = ", ".join(missing_settings)
        raise RuntimeError(
            f"Missing required production environment variables: {missing_names}."
        )


def _handle_csrf_error(_error: CSRFError) -> tuple[str, int]:
    return render_template("errors/csrf.html"), 400


def _handle_rate_limit_error(_error: TooManyRequests) -> tuple[str, int]:
    return render_template("errors/429.html"), 429


def _handle_forbidden_error(_error: Forbidden) -> tuple[str, int]:
    return render_template("errors/403.html"), 403


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
