from flask_wtf import FlaskForm
from wtforms import IntegerField, SelectField, StringField, SubmitField, TextAreaField
from wtforms.validators import DataRequired, InputRequired, NumberRange, ValidationError

from app.models import (
    RACK_CAPACITY_U_MAX,
    RACK_CAPACITY_U_MIN,
    RACK_STATUS_CHOICES,
    RackStatus,
    normalize_rack_code,
    normalize_rack_description,
    normalize_rack_name,
)


class RackForm(FlaskForm):
    room_id = SelectField(
        "Sala",
        coerce=int,
        validators=[DataRequired(message="Selecione uma Sala válida.")],
    )
    name = StringField(
        "Nome", validators=[DataRequired(message="Informe um nome válido.")]
    )
    code = StringField(
        "Código", validators=[DataRequired(message="Informe um código válido.")]
    )
    capacity_u = IntegerField(
        "Capacidade em U",
        validators=[
            InputRequired(message="Informe uma capacidade válida."),
            NumberRange(
                min=RACK_CAPACITY_U_MIN,
                max=RACK_CAPACITY_U_MAX,
                message="A capacidade deve estar entre 1 e 100 U.",
            ),
        ],
    )
    description = TextAreaField("Descrição")
    status = SelectField(
        "Status",
        choices=RACK_STATUS_CHOICES,
        default=RackStatus.ACTIVE.value,
        validators=[DataRequired(message="Informe um status válido.")],
    )
    submit = SubmitField("Salvar")

    def validate_name(self, field: StringField) -> None:
        try:
            field.data = normalize_rack_name(field.data)
        except ValueError as error:
            raise ValidationError("Informe um nome válido.") from error

    def validate_code(self, field: StringField) -> None:
        try:
            field.data = normalize_rack_code(field.data)
        except ValueError as error:
            raise ValidationError("Informe um código válido.") from error

    def validate_description(self, field: TextAreaField) -> None:
        try:
            field.data = normalize_rack_description(field.data)
        except ValueError as error:
            raise ValidationError("A descrição é muito longa.") from error
