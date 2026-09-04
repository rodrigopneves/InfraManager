from flask_wtf import FlaskForm
from wtforms import IntegerField, SelectField, StringField, SubmitField, TextAreaField
from wtforms.validators import DataRequired, InputRequired, ValidationError

from app.models import (
    VIRTUAL_MACHINE_DISK_GB_MAX,
    VIRTUAL_MACHINE_DISK_GB_MIN,
    VIRTUAL_MACHINE_ENVIRONMENT_CHOICES,
    VIRTUAL_MACHINE_MEMORY_MB_MAX,
    VIRTUAL_MACHINE_MEMORY_MB_MIN,
    VIRTUAL_MACHINE_STATUS_CHOICES,
    VIRTUAL_MACHINE_VCPU_MAX,
    VIRTUAL_MACHINE_VCPU_MIN,
    VirtualMachineStatus,
    normalize_virtual_machine_description,
    normalize_virtual_machine_hostname,
    normalize_virtual_machine_ip_address,
    normalize_virtual_machine_name,
    normalize_virtual_machine_operating_system,
)


class VirtualMachineForm(FlaskForm):
    host_asset_id = SelectField(
        "Host físico",
        coerce=int,
        validators=[DataRequired(message="Selecione um host físico válido.")],
    )
    name = StringField(
        "Nome", validators=[DataRequired(message="Informe um nome válido.")]
    )
    hostname = StringField("Hostname")
    ip_address = StringField("Endereço IP")
    operating_system = StringField("Sistema Operacional")
    vcpu = IntegerField(
        "vCPU", validators=[InputRequired(message="Informe uma quantidade de vCPU válida.")]
    )
    memory_mb = IntegerField(
        "Memória (MB)",
        validators=[InputRequired(message="Informe uma quantidade de memória válida.")],
    )
    disk_gb = IntegerField(
        "Disco (GB)",
        validators=[InputRequired(message="Informe uma quantidade de disco válida.")],
    )
    environment = SelectField(
        "Ambiente",
        choices=VIRTUAL_MACHINE_ENVIRONMENT_CHOICES,
        validators=[DataRequired(message="Informe um ambiente válido.")],
    )
    status = SelectField(
        "Status",
        choices=VIRTUAL_MACHINE_STATUS_CHOICES,
        default=VirtualMachineStatus.STOPPED.value,
        validators=[DataRequired(message="Informe um status válido.")],
    )
    description = TextAreaField("Descrição")
    submit = SubmitField("Salvar")

    def validate_name(self, field: StringField) -> None:
        try:
            field.data = normalize_virtual_machine_name(field.data)
        except ValueError as error:
            raise ValidationError("Informe um nome válido.") from error

    def validate_hostname(self, field: StringField) -> None:
        try:
            field.data = normalize_virtual_machine_hostname(field.data)
        except ValueError as error:
            raise ValidationError(
                "O hostname deve possuir no máximo 253 caracteres."
            ) from error

    def validate_ip_address(self, field: StringField) -> None:
        try:
            field.data = normalize_virtual_machine_ip_address(field.data)
        except ValueError as error:
            raise ValidationError("Informe um endereço IPv4 ou IPv6 válido.") from error

    def validate_operating_system(self, field: StringField) -> None:
        try:
            field.data = normalize_virtual_machine_operating_system(field.data)
        except ValueError as error:
            raise ValidationError(
                "O sistema operacional deve possuir no máximo 120 caracteres."
            ) from error

    def validate_vcpu(self, field: IntegerField) -> None:
        if (
            field.data is not None
            and not VIRTUAL_MACHINE_VCPU_MIN
            <= field.data
            <= VIRTUAL_MACHINE_VCPU_MAX
        ):
            raise ValidationError("vCPU deve estar entre 1 e 512.")

    def validate_memory_mb(self, field: IntegerField) -> None:
        if (
            field.data is not None
            and not VIRTUAL_MACHINE_MEMORY_MB_MIN
            <= field.data
            <= VIRTUAL_MACHINE_MEMORY_MB_MAX
        ):
            raise ValidationError("Memória deve estar entre 128 e 4194304 MB.")

    def validate_disk_gb(self, field: IntegerField) -> None:
        if (
            field.data is not None
            and not VIRTUAL_MACHINE_DISK_GB_MIN
            <= field.data
            <= VIRTUAL_MACHINE_DISK_GB_MAX
        ):
            raise ValidationError("Disco deve estar entre 1 e 1048576 GB.")

    def validate_description(self, field: TextAreaField) -> None:
        try:
            field.data = normalize_virtual_machine_description(field.data)
        except ValueError as error:
            raise ValidationError("A descrição é muito longa.") from error
