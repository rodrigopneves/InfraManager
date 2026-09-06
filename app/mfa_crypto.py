from cryptography.fernet import Fernet, InvalidToken
from flask import current_app


MFA_SECRET_PREFIX = "fernet:v1:"


class MfaEncryptionError(RuntimeError):
    pass


class LegacyMfaSecretError(MfaEncryptionError):
    pass


def validate_mfa_encryption_key(key: str | None) -> None:
    if not isinstance(key, str) or not key:
        raise MfaEncryptionError("MFA encryption key is not configured.")
    try:
        Fernet(key.encode("ascii"))
    except (UnicodeError, ValueError) as error:
        raise MfaEncryptionError("MFA encryption key is invalid.") from error


def encrypt_mfa_secret(secret: str) -> str:
    return encrypt_mfa_secret_with_key(
        secret, current_app.config.get("MFA_ENCRYPTION_KEY")
    )


def encrypt_mfa_secret_with_key(secret: str, key: str | None) -> str:
    if not isinstance(secret, str) or not secret:
        raise MfaEncryptionError("MFA secret is invalid.")
    try:
        encoded_secret = secret.encode("ascii")
    except UnicodeError as error:
        raise MfaEncryptionError("MFA secret is invalid.") from error
    token = _get_fernet(key).encrypt(encoded_secret).decode("ascii")
    return f"{MFA_SECRET_PREFIX}{token}"


def decrypt_mfa_secret(stored_secret: str) -> str:
    return decrypt_mfa_secret_with_key(
        stored_secret, current_app.config.get("MFA_ENCRYPTION_KEY")
    )


def decrypt_mfa_secret_with_key(stored_secret: str, key: str | None) -> str:
    if not stored_secret.startswith(MFA_SECRET_PREFIX):
        raise LegacyMfaSecretError("Stored MFA secret requires migration.")
    token = stored_secret.removeprefix(MFA_SECRET_PREFIX)
    try:
        return _get_fernet(key).decrypt(token.encode("ascii")).decode("ascii")
    except (InvalidToken, UnicodeError, ValueError) as error:
        raise MfaEncryptionError("Stored MFA secret could not be decrypted.") from error


def is_legacy_mfa_secret(stored_secret: str | None) -> bool:
    return bool(stored_secret) and not stored_secret.startswith(MFA_SECRET_PREFIX)


def _get_fernet(key: str | None) -> Fernet:
    validate_mfa_encryption_key(key)
    return Fernet(key.encode("ascii"))
