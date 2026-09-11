from flask import Blueprint, Response, current_app, redirect, url_for
from flask_login import current_user
from sqlalchemy import text
from sqlalchemy.exc import SQLAlchemyError

from app.extensions import db


main = Blueprint("main", __name__)


@main.get("/")
def index() -> Response:
    if current_user.is_authenticated:
        return redirect(url_for("auth.dashboard"))
    return redirect(url_for("auth.login"))


@main.get("/health")
def health() -> tuple[dict[str, str], int] | dict[str, str]:
    try:
        db.session.execute(text("SELECT 1"))
    except SQLAlchemyError:
        db.session.rollback()
        current_app.logger.error("Health check database query failed.")
        return {"status": "unavailable"}, 503
    return {"status": "ok"}
