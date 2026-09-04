from flask import Blueprint


asset = Blueprint("asset", __name__, url_prefix="/assets")

from app.asset import routes

__all__ = ["asset"]
