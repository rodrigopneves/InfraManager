from flask import Blueprint

from app.extensions import db, login_manager
from app.models import User


auth = Blueprint("auth", __name__)


@login_manager.user_loader
def load_user(user_id: str) -> User | None:
    try:
        return db.session.get(User, int(user_id))
    except (TypeError, ValueError):
        return None


from app.auth import routes

__all__ = ["auth"]
