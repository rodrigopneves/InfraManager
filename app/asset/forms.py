from flask_wtf import FlaskForm
from wtforms import IntegerField, SelectField, StringField, SubmitField, TextAreaField
from wtforms.validators import DataRequired, InputRequired, ValidationError

from app.models import (
    ASSET_STATUS_CHOICES,
    ASSET_TYPE_CHOICES,
    AssetStatus,
    normalize_asset_description,
    normalize_asset_name,
    normalize_asset_optional_text,
    normalize_asset_tag,
)


class AssetForm(FlaskForm):
    rack_id = SelectField(
        "Rack",
        coerce=int,
        validators=[DataRequired(message="Selecione um Rack válido.")],
    )
    name = StringField(
        "Nome", validators=[DataRequired(message="Informe um nome válido.")]
    )
    asset_tag = StringField(
        "Patrimônio/Identificador",
        validators=[DataRequired(message="Informe um identificador válido.")],
    )
    serial_number = StringField("Número de série")
    manufacturer = StringField("Fabricante")
    model = StringField("Modelo")
    asset_type = SelectField(
        "Tipo",
        choices=ASSET_TYPE_CHOICES,
        validators=[DataRequired(message="Informe um tipo válido.")],
    )
    rack_unit_start = IntegerField(
        "U inicial",
        validators=[InputRequired(message="Informe uma posição inicial válida.")],
    )
    rack_units = IntegerField(
        "Quantidade de U",
        validators=[InputRequired(message="Informe uma quantidade de U válida.")],
    )
    status = SelectField(
        "Status",
        choices=ASSET_STATUS_CHOICES,
        default=AssetStatus.ACTIVE.value,
        validators=[DataRequired(message="Informe um status válido.")],
    )
    description = TextAreaField("Descrição")
    submit = SubmitField("Salvar")

    def validate_name(self, field: StringField) -> None:
        try:
            field.data = normalize_asset_name(field.data)
        except ValueError as error:
            raise ValidationError("Informe um nome válido.") from error

    def validate_asset_tag(self, field: StringField) -> None:
        try:
            field.data = normalize_asset_tag(field.data)
        except ValueError as error:
            raise ValidationError("Informe um identificador válido.") from error

    def validate_serial_number(self, field: StringField) -> None:
        self._normalize_optional(field, "serial number")

    def validate_manufacturer(self, field: StringField) -> None:
        self._normalize_optional(field, "manufacturer")

    def validate_model(self, field: StringField) -> None:
        self._normalize_optional(field, "model")

    def validate_rack_unit_start(self, field: IntegerField) -> None:
        if field.data is not None and field.data < 1:
            raise ValidationError("A posição inicial deve ser maior ou igual a 1.")

    def validate_rack_units(self, field: IntegerField) -> None:
        if field.data is not None and field.data < 1:
            raise ValidationError("A quantidade de U deve ser maior ou igual a 1.")

    def validate_description(self, field: TextAreaField) -> None:
        try:
            field.data = normalize_asset_description(field.data)
        except ValueError as error:
            raise ValidationError("A descrição é muito longa.") from error

    @staticmethod
    def _normalize_optional(field: StringField, field_name: str) -> None:
        try:
            field.data = normalize_asset_optional_text(
                field.data, field=f"Asset {field_name}"
            )
        except ValueError as error:
            raise ValidationError("O campo deve possuir no máximo 120 caracteres.") from error
