from flask import Blueprint, current_app, render_template
from sqlalchemy import text
from sqlalchemy.exc import SQLAlchemyError

from app.extensions import db


main = Blueprint("main", __name__)


@main.get("/")
def index() -> str:
    return render_template("base.html")


@main.get("/health")
def health() -> tuple[dict[str, str], int] | dict[str, str]:
    try:
        db.session.execute(text("SELECT 1"))
    except SQLAlchemyError:
        db.session.rollback()
        current_app.logger.error("Health check database query failed.")
        return {"status": "unavailable"}, 503
    return {"status": "ok"}
