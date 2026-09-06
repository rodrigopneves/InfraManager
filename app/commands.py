import click
from flask.cli import with_appcontext
from sqlalchemy.exc import SQLAlchemyError

from app.admin.services import create_user
from app.extensions import db
from app.mfa_crypto import (
    MfaEncryptionError,
    decrypt_mfa_secret_with_key,
    encrypt_mfa_secret,
    encrypt_mfa_secret_with_key,
    is_legacy_mfa_secret,
    validate_mfa_encryption_key,
)
from app.models import User, UserRole, validate_email, validate_username


@click.command("create-admin")
@with_appcontext
def create_admin_command() -> None:
    username_input = click.prompt("Username")
    email_input = click.prompt("Email")

    try:
        username = validate_username(username_input)
        email = validate_email(email_input)
    except ValueError as error:
        raise click.ClickException("Username ou e-mail inválido.") from error

    if db.session.scalar(db.select(User).where(User.username == username)) is not None:
        raise click.ClickException("Username já cadastrado.")
    if db.session.scalar(db.select(User).where(User.email == email)) is not None:
        raise click.ClickException("E-mail já cadastrado.")

    password = click.prompt(
        "Password", hide_input=True, confirmation_prompt="Repeat for confirmation"
    )
    if len(password) < 8:
        raise click.ClickException("A senha deve possuir pelo menos 8 caracteres.")

    create_user(
        username=username,
        email=email,
        password=password,
        is_active=True,
        role=UserRole.ADMIN.value,
        source="cli",
    )
    click.echo("Administrador criado com sucesso.")


@click.command("encrypt-mfa-secrets")
@with_appcontext
def encrypt_mfa_secrets_command() -> None:
    users = db.session.scalars(
        db.select(User).where(User._mfa_secret.is_not(None))
    ).all()
    legacy_users = [
        user for user in users if is_legacy_mfa_secret(user._mfa_secret)
    ]
    try:
        for user in legacy_users:
            user._mfa_secret = encrypt_mfa_secret(user._mfa_secret)
        db.session.commit()
    except (MfaEncryptionError, SQLAlchemyError) as error:
        db.session.rollback()
        raise click.ClickException(
            "Não foi possível migrar os segredos MFA."
        ) from error
    click.echo(f"Segredos MFA migrados: {len(legacy_users)}.")


@click.command("rotate-mfa-key")
@with_appcontext
def rotate_mfa_key_command() -> None:
    old_key = click.prompt("Current MFA encryption key", hide_input=True)
    new_key = click.prompt(
        "New MFA encryption key",
        hide_input=True,
        confirmation_prompt="Repeat new MFA encryption key",
    )
    try:
        validate_mfa_encryption_key(old_key)
        validate_mfa_encryption_key(new_key)
    except MfaEncryptionError as error:
        raise click.ClickException("Chave Fernet inválida.") from error
    if old_key == new_key:
        raise click.ClickException("A nova chave deve ser diferente da atual.")

    users = db.session.scalars(
        db.select(User).where(User._mfa_secret.is_not(None))
    ).all()
    if any(is_legacy_mfa_secret(user._mfa_secret) for user in users):
        raise click.ClickException(
            "Existem segredos MFA legados; execute encrypt-mfa-secrets antes."
        )

    try:
        decrypted_secrets = [
            (user, decrypt_mfa_secret_with_key(user._mfa_secret, old_key))
            for user in users
        ]
        rotated_secrets = [
            (user, encrypt_mfa_secret_with_key(secret, new_key))
            for user, secret in decrypted_secrets
        ]
        for user, rotated_secret in rotated_secrets:
            user._mfa_secret = rotated_secret
        db.session.commit()
    except (MfaEncryptionError, SQLAlchemyError) as error:
        db.session.rollback()
        raise click.ClickException(
            "Não foi possível rotacionar os segredos MFA."
        ) from error
    click.echo(f"Segredos MFA rotacionados: {len(rotated_secrets)}.")
