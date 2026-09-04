from flask_wtf import FlaskForm
from wtforms import SelectField, StringField, SubmitField, TextAreaField
from wtforms.validators import DataRequired, ValidationError

from app.models import (
    DATACENTER_STATUS_CHOICES,
    DatacenterStatus,
    normalize_datacenter_code,
    normalize_datacenter_description,
    normalize_datacenter_location,
    normalize_datacenter_name,
)


class DatacenterForm(FlaskForm):
    name = StringField(
        "Nome", validators=[DataRequired(message="Informe um nome válido.")]
    )
    code = StringField(
        "Código", validators=[DataRequired(message="Informe um código válido.")]
    )
    location = StringField(
        "Localização",
        validators=[DataRequired(message="Informe uma localização válida.")],
    )
    description = TextAreaField("Descrição")
    status = SelectField(
        "Status",
        choices=DATACENTER_STATUS_CHOICES,
        default=DatacenterStatus.ACTIVE.value,
        validators=[DataRequired(message="Informe um status válido.")],
    )
    submit = SubmitField("Salvar")

    def validate_name(self, field: StringField) -> None:
        try:
            field.data = normalize_datacenter_name(field.data)
        except ValueError as error:
            raise ValidationError("Informe um nome válido.") from error

    def validate_code(self, field: StringField) -> None:
        try:
            field.data = normalize_datacenter_code(field.data)
        except ValueError as error:
            raise ValidationError("Informe um código válido.") from error

    def validate_location(self, field: StringField) -> None:
        try:
            field.data = normalize_datacenter_location(field.data)
        except ValueError as error:
            raise ValidationError("Informe uma localização válida.") from error

    def validate_description(self, field: TextAreaField) -> None:
        try:
            field.data = normalize_datacenter_description(field.data)
        except ValueError as error:
            raise ValidationError("A descrição é muito longa.") from error
