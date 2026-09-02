import logging
import os

from flask import Flask

import app.models
from app.extensions import csrf, db, login_manager, migrate
from config import CONFIGURATIONS, ProductionConfig


def create_app(config: str | object | None = None) -> Flask:
    app = Flask(__name__, instance_relative_config=True)
    selected_config = _resolve_config(config)
    app.config.from_object(selected_config)

    if selected_config is ProductionConfig and not app.config.get(
        "SQLALCHEMY_DATABASE_URI"
    ):
        raise RuntimeError(
            "DATABASE_URL must be defined when using the production configuration."
        )

    _configure_logging(app)
    db.init_app(app)
    migrate.init_app(app, db)
    login_manager.init_app(app)
    csrf.init_app(app)

    from app.auth import auth
    from app.routes import main

    app.register_blueprint(auth)
    app.register_blueprint(main)

    return app


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
