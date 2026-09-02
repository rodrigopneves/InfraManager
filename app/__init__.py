import os

from flask import Flask

from app.extensions import db, migrate
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

    db.init_app(app)
    migrate.init_app(app, db)

    from app.routes import main

    app.register_blueprint(main)

    return app


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
