from flask_wtf import FlaskForm
from wtforms import PasswordField, StringField, SubmitField
from wtforms.validators import DataRequired, Regexp


class MfaCodeForm(FlaskForm):
    code = StringField(
        "Código de autenticação",
        validators=[
            DataRequired(),
            Regexp(r"^\d{6}$", message="Código inválido."),
        ],
    )
    submit = SubmitField("Ativar MFA")


class DisableMfaForm(MfaCodeForm):
    password = PasswordField("Senha atual", validators=[DataRequired()])
    submit = SubmitField("Desativar MFA")
