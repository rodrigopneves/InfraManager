from flask import Blueprint


room = Blueprint("room", __name__, url_prefix="/rooms")

from app.room import routes

__all__ = ["room"]
