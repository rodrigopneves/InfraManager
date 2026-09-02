from flask_wtf import FlaskForm
from wtforms import PasswordField, StringField, SubmitField
from wtforms.validators import DataRequired, Length


class LoginForm(FlaskForm):
    username = StringField(
        "Usuário", validators=[DataRequired(), Length(max=80)]
    )
    password = PasswordField("Senha", validators=[DataRequired()])
    submit = SubmitField("Entrar")
