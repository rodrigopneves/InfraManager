import binascii
import time

import pyotp
from flask import current_app, session

from app.extensions import db
from app.models import User


PENDING_MFA_USER_ID_KEY = "pending_mfa_user_id"
PENDING_MFA_STARTED_AT_KEY = "pending_mfa_started_at"


def clear_pending_mfa_login() -> None:
    session.pop(PENDING_MFA_USER_ID_KEY, None)
    session.pop(PENDING_MFA_STARTED_AT_KEY, None)


def start_pending_mfa_login(user: User) -> None:
    session.clear()
    session[PENDING_MFA_USER_ID_KEY] = user.id
    session[PENDING_MFA_STARTED_AT_KEY] = int(time.time())


def get_pending_mfa_user() -> User | None:
    user_id = session.get(PENDING_MFA_USER_ID_KEY)
    started_at = session.get(PENDING_MFA_STARTED_AT_KEY)

    if not isinstance(user_id, int) or not isinstance(started_at, int):
        clear_pending_mfa_login()
        return None

    elapsed = int(time.time()) - started_at
    ttl = current_app.config["MFA_PENDING_TTL_SECONDS"]
    if elapsed < 0 or elapsed > ttl:
        clear_pending_mfa_login()
        return None

    user = db.session.get(User, user_id)
    if (
        user is None
        or not user.is_active
        or not user.mfa_enabled
        or not user.mfa_secret
    ):
        clear_pending_mfa_login()
        return None

    return user


def verify_totp(secret: str, code: str) -> bool:
    try:
        return pyotp.TOTP(secret).verify(code, valid_window=1)
    except (binascii.Error, TypeError, ValueError):
        return False
