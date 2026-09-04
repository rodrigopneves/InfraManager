import re
from datetime import datetime, timezone
from enum import Enum

from flask_login import UserMixin
from sqlalchemy import false
from sqlalchemy.orm import validates
from werkzeug.security import check_password_hash, generate_password_hash

from app.extensions import db
from app.mfa_crypto import decrypt_mfa_secret, encrypt_mfa_secret


USERNAME_PATTERN = re.compile(r"^[a-z0-9._-]{3,64}$")
EMAIL_PATTERN = re.compile(r"^[^@\s]+@[^@\s]+\.[^@\s]+$")


class UserRole(str, Enum):
    ADMIN = "admin"
    OPERATOR = "operator"
    VIEWER = "viewer"


ROLE_LABELS = {
    UserRole.ADMIN.value: "Administrador",
    UserRole.OPERATOR.value: "Operador",
    UserRole.VIEWER.value: "Visualizador",
}
ROLE_CHOICES = tuple((role.value, ROLE_LABELS[role.value]) for role in UserRole)
VALID_USER_ROLES = frozenset(role.value for role in UserRole)


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
    __table_args__ = (
        db.CheckConstraint(
            "role IN ('admin', 'operator', 'viewer')",
            name="ck_users_role",
        ),
    )

    id = db.Column(db.Integer, primary_key=True)
    username = db.Column(db.String(80), nullable=False, unique=True)
    email = db.Column(db.String(255), nullable=False, unique=True)
    password_hash = db.Column(db.String(255), nullable=False)
    is_active = db.Column(db.Boolean, nullable=False, default=True)
    role = db.Column(
        db.String(20),
        nullable=False,
        default=UserRole.VIEWER.value,
        server_default=UserRole.VIEWER.value,
    )
    mfa_enabled = db.Column(
        db.Boolean, nullable=False, default=False, server_default=false()
    )
    _mfa_secret = db.Column("mfa_secret", db.String(255), nullable=True)
    mfa_last_used_step = db.Column(db.BigInteger, nullable=True)
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

    @validates("role")
    def validate_role(self, _key: str, role: str | UserRole) -> str:
        role_value = role.value if isinstance(role, UserRole) else role
        if role_value not in VALID_USER_ROLES:
            raise ValueError("Role has an invalid value.")
        return role_value

    def has_role(self, *roles: str | UserRole) -> bool:
        allowed_roles = {
            role.value if isinstance(role, UserRole) else role for role in roles
        }
        return self.role in allowed_roles

    @property
    def role_label(self) -> str:
        return ROLE_LABELS.get(self.role, "Perfil inválido")

    def set_password(self, password: str) -> None:
        self.password_hash = generate_password_hash(password)

    def check_password(self, password: str) -> bool:
        return check_password_hash(self.password_hash, password)

    @property
    def mfa_secret(self) -> str | None:
        if self._mfa_secret is None:
            return None
        return decrypt_mfa_secret(self._mfa_secret)

    @mfa_secret.setter
    def mfa_secret(self, secret: str | None) -> None:
        self._mfa_secret = encrypt_mfa_secret(secret) if secret is not None else None
        self.mfa_last_used_step = None

    @validates("mfa_last_used_step")
    def validate_mfa_last_used_step(self, _key: str, step: int | None) -> int | None:
        if step is None:
            return None
        if not isinstance(step, int) or isinstance(step, bool) or step < 0:
            raise ValueError("MFA last used step is invalid.")
        return step
