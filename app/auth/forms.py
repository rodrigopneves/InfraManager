from flask_wtf import FlaskForm
from wtforms import PasswordField, StringField, SubmitField
from wtforms.validators import DataRequired, Regexp, ValidationError

from app.models import validate_username as validate_username_value


class LoginForm(FlaskForm):
    username = StringField("Usuário", validators=[DataRequired()])
    password = PasswordField("Senha", validators=[DataRequired()])
    submit = SubmitField("Entrar")

    def validate_username(self, field: StringField) -> None:
        try:
            field.data = validate_username_value(field.data)
        except ValueError as error:
            raise ValidationError("Usuário inválido.") from error


class MfaVerifyForm(FlaskForm):
    code = StringField(
        "Código de autenticação",
        validators=[
            DataRequired(),
            Regexp(r"^\d{6}$", message="Código inválido."),
        ],
    )
    submit = SubmitField("Verificar")
