import re
from datetime import datetime, timezone

from flask_login import UserMixin
from sqlalchemy.orm import validates
from werkzeug.security import check_password_hash, generate_password_hash

from app.extensions import db


USERNAME_PATTERN = re.compile(r"^[a-z0-9._-]{3,64}$")
EMAIL_PATTERN = re.compile(r"^[^@\s]+@[^@\s]+\.[^@\s]+$")


def utc_now() -> datetime:
    return datetime.now(timezone.utc)


def normalize_username(username: str) -> str:
    if not isinstance(username, str):
        raise ValueError("Username must be a string.")
    return username.strip().lower()


def validate_username(username: str) -> str:
    normalized_username = normalize_username(username)
    if not USERNAME_PATTERN.fullmatch(normalized_username):
        raise ValueError("Username has an invalid format.")
    return normalized_username


def normalize_email(email: str) -> str:
    if not isinstance(email, str):
        raise ValueError("Email must be a string.")
    return email.strip().lower()


def validate_email(email: str) -> str:
    normalized_email = normalize_email(email)
    if len(normalized_email) > 255 or not EMAIL_PATTERN.fullmatch(normalized_email):
        raise ValueError("Email has an invalid format.")
    return normalized_email


class User(UserMixin, db.Model):
    __tablename__ = "users"

    id = db.Column(db.Integer, primary_key=True)
    username = db.Column(db.String(80), nullable=False, unique=True)
    email = db.Column(db.String(255), nullable=False, unique=True)
    password_hash = db.Column(db.String(255), nullable=False)
    is_active = db.Column(db.Boolean, nullable=False, default=True)
    created_at = db.Column(db.DateTime(timezone=True), nullable=False, default=utc_now)
    updated_at = db.Column(
        db.DateTime(timezone=True), nullable=False, default=utc_now, onupdate=utc_now
    )

    @validates("username")
    def normalize_and_validate_username(self, _key: str, username: str) -> str:
        return validate_username(username)

    @validates("email")
    def normalize_and_validate_email(self, _key: str, email: str) -> str:
        return validate_email(email)

    def set_password(self, password: str) -> None:
        self.password_hash = generate_password_hash(password)

    def check_password(self, password: str) -> bool:
        return check_password_hash(self.password_hash, password)
