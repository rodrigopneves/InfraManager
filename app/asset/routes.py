from flask import flash, redirect, render_template, request, url_for
from flask_login import current_user

from app.admin.decorators import admin_required, roles_required
from app.asset import asset
from app.asset.forms import AssetForm
from app.asset.services import (
    AssetRackCapacityError,
    AssetRackNotFoundError,
    AssetRackOverlapError,
    AssetHasVirtualMachinesError,
    AssetTagConflictError,
    asset_tag_exists,
    create_asset,
    delete_asset,
    get_asset_or_404,
    list_assets,
    list_racks_for_form,
    update_asset,
)
from app.models import UserRole


read_access_required = roles_required(
    UserRole.ADMIN, UserRole.OPERATOR, UserRole.VIEWER
)


def _set_rack_choices(form: AssetForm) -> set[int]:
    racks = list_racks_for_form()
    form.rack_id.choices = [
        (
            rack.id,
            f"{rack.room.datacenter.code} / {rack.room.code} / {rack.code}",
        )
        for rack in racks
    ]
    return {rack.id for rack in racks}


def _form_values(form: AssetForm) -> dict[str, object]:
    return {
        "rack_id": form.rack_id.data,
        "name": form.name.data,
        "asset_tag": form.asset_tag.data,
        "serial_number": form.serial_number.data,
        "manufacturer": form.manufacturer.data,
        "model": form.model.data,
        "asset_type": form.asset_type.data,
        "rack_unit_start": form.rack_unit_start.data,
        "rack_units": form.rack_units.data,
        "description": form.description.data,
        "status": form.status.data,
    }


def _apply_service_error(form: AssetForm, error: ValueError) -> None:
    if isinstance(error, AssetRackNotFoundError):
        form.rack_id.errors.append(str(error))
    elif isinstance(error, AssetTagConflictError):
        form.asset_tag.errors.append(str(error))
    elif isinstance(error, AssetHasVirtualMachinesError):
        form.asset_type.errors.append(str(error))
    else:
        form.rack_units.errors.append(str(error))


@asset.get("")
@read_access_required
def index():
    page = request.args.get("page", 1, type=int)
    pagination = list_assets(page)
    return render_template(
        "asset/index.html", pagination=pagination, admin_role=UserRole.ADMIN
    )


@asset.get("/<int:asset_id>")
@read_access_required
def detail(asset_id: int):
    selected_asset = get_asset_or_404(asset_id)
    return render_template(
        "asset/detail.html", asset=selected_asset, admin_role=UserRole.ADMIN
    )


@asset.route("/create", methods=["GET", "POST"])
@admin_required
def create():
    form = AssetForm()
    valid_rack_ids = _set_rack_choices(form)
    if request.method == "GET":
        requested_rack_id = request.args.get("rack_id", type=int)
        if requested_rack_id in valid_rack_ids:
            form.rack_id.data = requested_rack_id

    if form.validate_on_submit():
        if asset_tag_exists(form.asset_tag.data):
            form.asset_tag.errors.append(
                "Já existe um Ativo com este patrimônio/identificador."
            )
        else:
            try:
                created_asset = create_asset(current_user, **_form_values(form))
            except (
                AssetRackNotFoundError,
                AssetTagConflictError,
                AssetRackCapacityError,
                AssetRackOverlapError,
            ) as error:
                _apply_service_error(form, error)
            else:
                flash("Ativo criado com sucesso.", "success")
                return redirect(
                    url_for("asset.detail", asset_id=created_asset.id)
                )

    return render_template(
        "asset/form.html",
        form=form,
        title="Novo Ativo",
        cancel_url=url_for("asset.index"),
    )


@asset.route("/<int:asset_id>/edit", methods=["GET", "POST"])
@admin_required
def edit(asset_id: int):
    selected_asset = get_asset_or_404(asset_id)
    form = AssetForm(obj=selected_asset)
    _set_rack_choices(form)

    if form.validate_on_submit():
        if asset_tag_exists(
            form.asset_tag.data, exclude_asset_id=selected_asset.id
        ):
            form.asset_tag.errors.append(
                "Já existe um Ativo com este patrimônio/identificador."
            )
        else:
            try:
                update_asset(
                    current_user, selected_asset, **_form_values(form)
                )
            except (
                AssetRackNotFoundError,
                AssetTagConflictError,
                AssetRackCapacityError,
                AssetRackOverlapError,
                AssetHasVirtualMachinesError,
            ) as error:
                _apply_service_error(form, error)
            else:
                flash("Ativo atualizado com sucesso.", "success")
                return redirect(
                    url_for("asset.detail", asset_id=selected_asset.id)
                )

    return render_template(
        "asset/form.html",
        form=form,
        title="Editar Ativo",
        cancel_url=url_for("asset.detail", asset_id=selected_asset.id),
    )


@asset.post("/<int:asset_id>/delete")
@admin_required
def delete(asset_id: int):
    selected_asset = get_asset_or_404(asset_id)
    try:
        delete_asset(current_user, selected_asset)
    except AssetHasVirtualMachinesError as error:
        flash(str(error), "error")
        return redirect(url_for("asset.detail", asset_id=selected_asset.id))
    flash("Ativo excluído com sucesso.", "success")
    return redirect(url_for("asset.index"))


@asset.get("/<int:asset_id>/delete-confirm")
@admin_required
def delete_confirm(asset_id: int):
    selected_asset = get_asset_or_404(asset_id)
    return render_template("asset/delete_confirm.html", asset=selected_asset)
