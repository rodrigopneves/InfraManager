from flask_wtf import FlaskForm
from wtforms import BooleanField, PasswordField, SelectField, StringField, SubmitField
from wtforms.validators import DataRequired, EqualTo, Length, ValidationError

from app.models import ROLE_CHOICES
from app.models import validate_email as validate_email_value
from app.models import validate_username as validate_username_value


class UserFieldsForm(FlaskForm):
    username = StringField(
        "Usuário", validators=[DataRequired(message="Informe um usuário.")]
    )
    email = StringField(
        "E-mail", validators=[DataRequired(message="Informe um e-mail.")]
    )
    is_active = BooleanField("Ativo", default=True)
    role = SelectField(
        "Perfil",
        choices=ROLE_CHOICES,
        validators=[DataRequired(message="Selecione um perfil.")],
    )

    def validate_username(self, field: StringField) -> None:
        try:
            field.data = validate_username_value(field.data)
        except ValueError as error:
            raise ValidationError("Nome de usuário inválido.") from error

    def validate_email(self, field: StringField) -> None:
        try:
            field.data = validate_email_value(field.data)
        except ValueError as error:
            raise ValidationError("E-mail inválido.") from error


class CreateUserForm(UserFieldsForm):
    password = PasswordField(
        "Senha",
        validators=[
            DataRequired(message="Informe uma senha."),
            Length(
                min=8,
                max=256,
                message="A senha deve possuir entre 8 e 256 caracteres.",
            ),
        ],
    )
    password_confirmation = PasswordField(
        "Confirmar senha",
        validators=[
            DataRequired(message="Confirme a senha."),
            EqualTo("password", message="As senhas devem coincidir."),
        ],
    )
    submit = SubmitField("Criar usuário")


class EditUserForm(UserFieldsForm):
    submit = SubmitField("Salvar alterações")
