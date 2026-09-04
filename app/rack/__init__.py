from flask import Blueprint


rack = Blueprint("rack", __name__, url_prefix="/racks")

from app.rack import routes

__all__ = ["rack"]
