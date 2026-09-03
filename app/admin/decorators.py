from functools import wraps

from flask import abort
from flask_login import current_user, login_required

from app.models import UserRole


def roles_required(*allowed_roles: str | UserRole):
    def decorator(view):
        @login_required
        @wraps(view)
        def wrapped_view(*args, **kwargs):
            if not current_user.has_role(*allowed_roles):
                abort(403)
            return view(*args, **kwargs)

        return wrapped_view

    return decorator


admin_required = roles_required(UserRole.ADMIN)
