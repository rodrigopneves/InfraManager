import click
from flask.cli import with_appcontext

from app.admin.services import create_user
from app.extensions import db
from app.models import User, validate_email, validate_username


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
        is_admin=True,
    )
    click.echo("Administrador criado com sucesso.")
