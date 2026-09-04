from flask import flash, redirect, render_template, request, url_for
from flask_login import current_user

from app.admin.decorators import admin_required, roles_required
from app.models import UserRole
from app.virtual_machine import virtual_machine
from app.virtual_machine.forms import VirtualMachineForm
from app.virtual_machine.services import (
    VirtualMachineHostNotFoundError,
    VirtualMachineInvalidHostError,
    VirtualMachineInvalidIPAddressError,
    VirtualMachineNameConflictError,
    create_virtual_machine,
    delete_virtual_machine,
    get_virtual_machine_or_404,
    list_eligible_hosts,
    list_virtual_machines,
    update_virtual_machine,
    virtual_machine_name_exists,
)


read_access_required = roles_required(
    UserRole.ADMIN, UserRole.OPERATOR, UserRole.VIEWER
)


def _set_host_choices(form: VirtualMachineForm) -> set[int]:
    hosts = list_eligible_hosts()
    form.host_asset_id.choices = [
        (
            host.id,
            f"{host.rack.room.datacenter.code} / {host.rack.room.code} / "
            f"{host.rack.code} / {host.asset_tag}",
        )
        for host in hosts
    ]
    return {host.id for host in hosts}


def _form_values(form: VirtualMachineForm) -> dict[str, object]:
    return {
        "host_asset_id": form.host_asset_id.data,
        "name": form.name.data,
        "hostname": form.hostname.data,
        "ip_address": form.ip_address.data,
        "operating_system": form.operating_system.data,
        "vcpu": form.vcpu.data,
        "memory_mb": form.memory_mb.data,
        "disk_gb": form.disk_gb.data,
        "environment": form.environment.data,
        "status": form.status.data,
        "description": form.description.data,
    }


def _apply_service_error(form: VirtualMachineForm, error: ValueError) -> None:
    if isinstance(
        error, (VirtualMachineHostNotFoundError, VirtualMachineInvalidHostError)
    ):
        form.host_asset_id.errors.append(str(error))
    elif isinstance(error, VirtualMachineNameConflictError):
        form.name.errors.append(str(error))
    else:
        form.ip_address.errors.append(str(error))


@virtual_machine.get("")
@read_access_required
def index():
    page = request.args.get("page", 1, type=int)
    pagination = list_virtual_machines(page)
    return render_template(
        "virtual_machine/index.html",
        pagination=pagination,
        admin_role=UserRole.ADMIN,
    )


@virtual_machine.get("/<int:virtual_machine_id>")
@read_access_required
def detail(virtual_machine_id: int):
    selected_virtual_machine = get_virtual_machine_or_404(virtual_machine_id)
    return render_template(
        "virtual_machine/detail.html",
        virtual_machine=selected_virtual_machine,
        admin_role=UserRole.ADMIN,
    )


@virtual_machine.route("/create", methods=["GET", "POST"])
@admin_required
def create():
    form = VirtualMachineForm()
    valid_host_ids = _set_host_choices(form)
    if request.method == "GET":
        requested_host_id = request.args.get("host_asset_id", type=int)
        if requested_host_id in valid_host_ids:
            form.host_asset_id.data = requested_host_id

    if form.validate_on_submit():
        if virtual_machine_name_exists(form.name.data):
            form.name.errors.append("Já existe uma Máquina Virtual com este nome.")
        else:
            try:
                created_virtual_machine = create_virtual_machine(
                    current_user, **_form_values(form)
                )
            except (
                VirtualMachineHostNotFoundError,
                VirtualMachineInvalidHostError,
                VirtualMachineInvalidIPAddressError,
                VirtualMachineNameConflictError,
            ) as error:
                _apply_service_error(form, error)
            else:
                flash("Máquina Virtual criada com sucesso.", "success")
                return redirect(
                    url_for(
                        "virtual_machine.detail",
                        virtual_machine_id=created_virtual_machine.id,
                    )
                )

    return render_template(
        "virtual_machine/form.html",
        form=form,
        title="Nova Máquina Virtual",
        cancel_url=url_for("virtual_machine.index"),
    )


@virtual_machine.route("/<int:virtual_machine_id>/edit", methods=["GET", "POST"])
@admin_required
def edit(virtual_machine_id: int):
    selected_virtual_machine = get_virtual_machine_or_404(virtual_machine_id)
    form = VirtualMachineForm(obj=selected_virtual_machine)
    _set_host_choices(form)

    if form.validate_on_submit():
        if virtual_machine_name_exists(
            form.name.data,
            exclude_virtual_machine_id=selected_virtual_machine.id,
        ):
            form.name.errors.append("Já existe uma Máquina Virtual com este nome.")
        else:
            try:
                update_virtual_machine(
                    current_user,
                    selected_virtual_machine,
                    **_form_values(form),
                )
            except (
                VirtualMachineHostNotFoundError,
                VirtualMachineInvalidHostError,
                VirtualMachineInvalidIPAddressError,
                VirtualMachineNameConflictError,
            ) as error:
                _apply_service_error(form, error)
            else:
                flash("Máquina Virtual atualizada com sucesso.", "success")
                return redirect(
                    url_for(
                        "virtual_machine.detail",
                        virtual_machine_id=selected_virtual_machine.id,
                    )
                )

    return render_template(
        "virtual_machine/form.html",
        form=form,
        title="Editar Máquina Virtual",
        cancel_url=url_for(
            "virtual_machine.detail",
            virtual_machine_id=selected_virtual_machine.id,
        ),
    )


@virtual_machine.get("/<int:virtual_machine_id>/delete-confirm")
@admin_required
def delete_confirm(virtual_machine_id: int):
    selected_virtual_machine = get_virtual_machine_or_404(virtual_machine_id)
    return render_template(
        "virtual_machine/delete_confirm.html",
        virtual_machine=selected_virtual_machine,
    )


@virtual_machine.post("/<int:virtual_machine_id>/delete")
@admin_required
def delete(virtual_machine_id: int):
    selected_virtual_machine = get_virtual_machine_or_404(virtual_machine_id)
    delete_virtual_machine(current_user, selected_virtual_machine)
    flash("Máquina Virtual excluída com sucesso.", "success")
    return redirect(url_for("virtual_machine.index"))
