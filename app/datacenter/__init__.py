from flask import Blueprint


datacenter = Blueprint("datacenter", __name__, url_prefix="/datacenters")

from app.datacenter import routes

__all__ = ["datacenter"]
