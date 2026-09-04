import binascii
import time

import pyotp
from flask import current_app, session
from sqlalchemy import or_
from werkzeug.security import check_password_hash, generate_password_hash

from app.extensions import db
from app.models import User


PENDING_MFA_USER_ID_KEY = "pending_mfa_user_id"
PENDING_MFA_STARTED_AT_KEY = "pending_mfa_started_at"
DUMMY_PASSWORD_HASH = generate_password_hash("dummy-password-not-used-by-any-account")


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
    if user is None or not user.is_active:
        clear_pending_mfa_login()
        return None

    return user


def get_valid_totp_step(
    secret: str, code: str, *, for_time: float | None = None
) -> int | None:
    try:
        totp = pyotp.TOTP(secret)
        timestamp = for_time if for_time is not None else time.time()
        current_step = int(timestamp) // totp.interval
        for offset in range(-1, 2):
            candidate_step = current_step + offset
            if candidate_step < 0:
                continue
            if pyotp.utils.strings_equal(totp.generate_otp(candidate_step), code):
                return candidate_step
    except (binascii.Error, TypeError, ValueError):
        pass
    return None


def verify_totp(secret: str, code: str) -> bool:
    return get_valid_totp_step(secret, code) is not None


def consume_totp(user: User, code: str) -> bool:
    secret = user.mfa_secret
    if not secret:
        return False
    step = get_valid_totp_step(secret, code)
    if step is None:
        return False
    result = db.session.execute(
        db.update(User)
        .where(
            User.id == user.id,
            or_(
                User.mfa_last_used_step.is_(None),
                User.mfa_last_used_step < step,
            ),
        )
        .values(mfa_last_used_step=step),
        execution_options={"synchronize_session": "fetch"},
    )
    return result.rowcount == 1


def verify_user_password(user: User | None, password: str) -> bool:
    if user is None or not user.is_active:
        check_password_hash(DUMMY_PASSWORD_HASH, password)
        return False
    return user.check_password(password)
