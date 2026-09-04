from flask import Blueprint


virtual_machine = Blueprint(
    "virtual_machine", __name__, url_prefix="/virtual-machines"
)

from app.virtual_machine import routes

__all__ = ["virtual_machine"]
