from cryptography.fernet import Fernet
import pyotp
import pytest

from app import create_app
from app.extensions import db
from app.mfa_crypto import (
    LegacyMfaSecretError,
    MFA_SECRET_PREFIX,
    MfaEncryptionError,
)
from app.models import User
from config import ProductionConfig


def raw_mfa_secret(user: User) -> str | None:
    return db.session.scalar(
        db.select(User._mfa_secret).where(User.id == user.id)
    )


def test_mfa_secret_is_encrypted_at_rest_and_round_trips(app) -> None:
    secret = pyotp.random_base32()
    user = User(username="encrypted.demo", email="encrypted.demo@example.com")
    user.set_password("valid-test-password")
    user.mfa_secret = secret
    user.mfa_enabled = True
    db.session.add(user)
    db.session.commit()

    stored_value = raw_mfa_secret(user)

    assert stored_value is not None
    assert stored_value.startswith(MFA_SECRET_PREFIX)
    assert secret not in stored_value
    assert user.mfa_secret == secret


def test_wrong_key_fails_closed_without_changing_or_exposing_secret(
    app, caplog: pytest.LogCaptureFixture
) -> None:
    secret = pyotp.random_base32()
    user = User(username="wrong-key.demo", email="wrong-key.demo@example.com")
    user.set_password("valid-test-password")
    user.mfa_secret = secret
    db.session.add(user)
    db.session.commit()
    stored_value = raw_mfa_secret(user)
    app.config["MFA_ENCRYPTION_KEY"] = Fernet.generate_key().decode("ascii")

    with pytest.raises(MfaEncryptionError) as error:
        _ = user.mfa_secret

    assert secret not in str(error.value)
    assert app.config["MFA_ENCRYPTION_KEY"] not in str(error.value)
    assert secret not in caplog.text
    assert app.config["MFA_ENCRYPTION_KEY"] not in caplog.text
    assert raw_mfa_secret(user) == stored_value


def test_legacy_plaintext_requires_explicit_migration(app) -> None:
    secret = pyotp.random_base32()
    user = User(username="legacy.demo", email="legacy.demo@example.com")
    user.set_password("valid-test-password")
    db.session.add(user)
    db.session.flush()
    db.session.execute(
        User.__table__.update()
        .where(User.id == user.id)
        .values(mfa_secret=secret, mfa_enabled=True)
    )
    db.session.commit()
    db.session.expire(user)

    with pytest.raises(LegacyMfaSecretError) as error:
        _ = user.mfa_secret

    assert secret not in str(error.value)


def test_cli_encrypts_legacy_secrets_once_without_printing_them(app) -> None:
    secret = pyotp.random_base32()
    user = User(username="cli-legacy.demo", email="cli-legacy.demo@example.com")
    user.set_password("valid-test-password")
    db.session.add(user)
    db.session.flush()
    db.session.execute(
        User.__table__.update()
        .where(User.id == user.id)
        .values(mfa_secret=secret, mfa_enabled=True)
    )
    db.session.commit()

    first_result = app.test_cli_runner().invoke(args=["encrypt-mfa-secrets"])
    db.session.expire_all()
    encrypted_value = raw_mfa_secret(user)
    second_result = app.test_cli_runner().invoke(args=["encrypt-mfa-secrets"])

    assert first_result.exit_code == 0
    assert "Segredos MFA migrados: 1." in first_result.output
    assert secret not in first_result.output
    assert encrypted_value is not None
    assert encrypted_value.startswith(MFA_SECRET_PREFIX)
    assert user.mfa_secret == secret
    assert second_result.exit_code == 0
    assert "Segredos MFA migrados: 0." in second_result.output


def test_production_rejects_invalid_mfa_encryption_key() -> None:
    class InvalidMfaKeyProductionConfig(ProductionConfig):
        SECRET_KEY = "production-test-only-secret"
        SQLALCHEMY_DATABASE_URI = "sqlite:///:memory:"
        MFA_ENCRYPTION_KEY = "invalid-key"

    with pytest.raises(RuntimeError, match="MFA encryption configuration"):
        create_app(InvalidMfaKeyProductionConfig)
