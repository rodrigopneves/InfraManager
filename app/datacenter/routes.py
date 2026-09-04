from flask import flash, redirect, render_template, request, url_for
from flask_login import current_user

from app.admin.decorators import admin_required, roles_required
from app.datacenter import datacenter
from app.datacenter.forms import DatacenterForm
from app.datacenter.services import (
    DatacenterCodeConflictError,
    create_datacenter,
    datacenter_code_exists,
    delete_datacenter,
    get_datacenter_or_404,
    list_datacenters,
    update_datacenter,
)
from app.models import UserRole


read_access_required = roles_required(
    UserRole.ADMIN, UserRole.OPERATOR, UserRole.VIEWER
)


@datacenter.get("")
@read_access_required
def index():
    page = request.args.get("page", 1, type=int)
    pagination = list_datacenters(page)
    return render_template(
        "datacenter/index.html",
        pagination=pagination,
        admin_role=UserRole.ADMIN,
    )


@datacenter.get("/<int:datacenter_id>")
@read_access_required
def detail(datacenter_id: int):
    selected_datacenter = get_datacenter_or_404(datacenter_id)
    return render_template(
        "datacenter/detail.html",
        datacenter=selected_datacenter,
        admin_role=UserRole.ADMIN,
    )


@datacenter.route("/create", methods=["GET", "POST"])
@admin_required
def create():
    form = DatacenterForm()
    if form.validate_on_submit():
        if datacenter_code_exists(form.code.data):
            form.code.errors.append("Já existe um Datacenter com este código.")
        else:
            try:
                created_datacenter = create_datacenter(
                    current_user,
                    name=form.name.data,
                    code=form.code.data,
                    location=form.location.data,
                    description=form.description.data,
                    status=form.status.data,
                )
            except DatacenterCodeConflictError as error:
                form.code.errors.append(str(error))
            else:
                flash("Datacenter criado com sucesso.", "success")
                return redirect(
                    url_for("datacenter.detail", datacenter_id=created_datacenter.id)
                )
    return render_template(
        "datacenter/form.html",
        form=form,
        title="Novo Datacenter",
        cancel_url=url_for("datacenter.index"),
    )


@datacenter.route("/<int:datacenter_id>/edit", methods=["GET", "POST"])
@admin_required
def edit(datacenter_id: int):
    selected_datacenter = get_datacenter_or_404(datacenter_id)
    form = DatacenterForm(obj=selected_datacenter)
    if form.validate_on_submit():
        if datacenter_code_exists(
            form.code.data, exclude_datacenter_id=selected_datacenter.id
        ):
            form.code.errors.append("Já existe um Datacenter com este código.")
        else:
            try:
                update_datacenter(
                    current_user,
                    selected_datacenter,
                    name=form.name.data,
                    code=form.code.data,
                    location=form.location.data,
                    description=form.description.data,
                    status=form.status.data,
                )
            except DatacenterCodeConflictError as error:
                form.code.errors.append(str(error))
            else:
                flash("Datacenter atualizado com sucesso.", "success")
                return redirect(
                    url_for("datacenter.detail", datacenter_id=selected_datacenter.id)
                )
    return render_template(
        "datacenter/form.html",
        form=form,
        title="Editar Datacenter",
        cancel_url=url_for(
            "datacenter.detail", datacenter_id=selected_datacenter.id
        ),
    )


@datacenter.post("/<int:datacenter_id>/delete")
@admin_required
def delete(datacenter_id: int):
    selected_datacenter = get_datacenter_or_404(datacenter_id)
    delete_datacenter(current_user, selected_datacenter)
    flash("Datacenter excluído com sucesso.", "success")
    return redirect(url_for("datacenter.index"))


@datacenter.get("/<int:datacenter_id>/delete-confirm")
@admin_required
def delete_confirm(datacenter_id: int):
    selected_datacenter = get_datacenter_or_404(datacenter_id)
    return render_template(
        "datacenter/delete_confirm.html", datacenter=selected_datacenter
    )
