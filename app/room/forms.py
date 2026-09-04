from flask_wtf import FlaskForm
from wtforms import SelectField, StringField, SubmitField, TextAreaField
from wtforms.validators import DataRequired, ValidationError

from app.models import (
    ROOM_STATUS_CHOICES,
    RoomStatus,
    normalize_room_code,
    normalize_room_description,
    normalize_room_name,
)


class RoomForm(FlaskForm):
    datacenter_id = SelectField(
        "Datacenter",
        coerce=int,
        validators=[DataRequired(message="Selecione um Datacenter válido.")],
    )
    name = StringField(
        "Nome", validators=[DataRequired(message="Informe um nome válido.")]
    )
    code = StringField(
        "Código", validators=[DataRequired(message="Informe um código válido.")]
    )
    description = TextAreaField("Descrição")
    status = SelectField(
        "Status",
        choices=ROOM_STATUS_CHOICES,
        default=RoomStatus.ACTIVE.value,
        validators=[DataRequired(message="Informe um status válido.")],
    )
    submit = SubmitField("Salvar")

    def validate_name(self, field: StringField) -> None:
        try:
            field.data = normalize_room_name(field.data)
        except ValueError as error:
            raise ValidationError("Informe um nome válido.") from error

    def validate_code(self, field: StringField) -> None:
        try:
            field.data = normalize_room_code(field.data)
        except ValueError as error:
            raise ValidationError("Informe um código válido.") from error

    def validate_description(self, field: TextAreaField) -> None:
        try:
            field.data = normalize_room_description(field.data)
        except ValueError as error:
            raise ValidationError("A descrição é muito longa.") from error
