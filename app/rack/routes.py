from flask import flash, redirect, render_template, request, url_for
from flask_login import current_user

from app.admin.decorators import admin_required, roles_required
from app.models import UserRole
from app.rack import rack
from app.rack.forms import RackForm
from app.rack.services import (
    RackCodeConflictError,
    RackRoomNotFoundError,
    create_rack,
    delete_rack,
    get_rack_or_404,
    list_racks,
    list_rooms_for_form,
    rack_code_exists,
    update_rack,
)


read_access_required = roles_required(
    UserRole.ADMIN, UserRole.OPERATOR, UserRole.VIEWER
)


def _set_room_choices(form: RackForm) -> set[int]:
    rooms = list_rooms_for_form()
    form.room_id.choices = [
        (
            room.id,
            f"{room.datacenter.code} / {room.code} — {room.name}",
        )
        for room in rooms
    ]
    return {room.id for room in rooms}


@rack.get("")
@read_access_required
def index():
    page = request.args.get("page", 1, type=int)
    pagination = list_racks(page)
    return render_template(
        "rack/index.html", pagination=pagination, admin_role=UserRole.ADMIN
    )


@rack.get("/<int:rack_id>")
@read_access_required
def detail(rack_id: int):
    selected_rack = get_rack_or_404(rack_id)
    return render_template(
        "rack/detail.html", rack=selected_rack, admin_role=UserRole.ADMIN
    )


@rack.route("/create", methods=["GET", "POST"])
@admin_required
def create():
    form = RackForm()
    valid_room_ids = _set_room_choices(form)
    if request.method == "GET":
        requested_room_id = request.args.get("room_id", type=int)
        if requested_room_id in valid_room_ids:
            form.room_id.data = requested_room_id

    if form.validate_on_submit():
        if rack_code_exists(form.room_id.data, form.code.data):
            form.code.errors.append(
                "Já existe um Rack com este código na Sala selecionada."
            )
        else:
            try:
                created_rack = create_rack(
                    current_user,
                    room_id=form.room_id.data,
                    name=form.name.data,
                    code=form.code.data,
                    capacity_u=form.capacity_u.data,
                    description=form.description.data,
                    status=form.status.data,
                )
            except RackRoomNotFoundError as error:
                form.room_id.errors.append(str(error))
            except RackCodeConflictError as error:
                form.code.errors.append(str(error))
            else:
                flash("Rack criado com sucesso.", "success")
                return redirect(url_for("rack.detail", rack_id=created_rack.id))

    return render_template(
        "rack/form.html",
        form=form,
        title="Novo Rack",
        cancel_url=url_for("rack.index"),
    )


@rack.route("/<int:rack_id>/edit", methods=["GET", "POST"])
@admin_required
def edit(rack_id: int):
    selected_rack = get_rack_or_404(rack_id)
    form = RackForm(obj=selected_rack)
    _set_room_choices(form)

    if form.validate_on_submit():
        if rack_code_exists(
            form.room_id.data,
            form.code.data,
            exclude_rack_id=selected_rack.id,
        ):
            form.code.errors.append(
                "Já existe um Rack com este código na Sala selecionada."
            )
        else:
            try:
                update_rack(
                    current_user,
                    selected_rack,
                    room_id=form.room_id.data,
                    name=form.name.data,
                    code=form.code.data,
                    capacity_u=form.capacity_u.data,
                    description=form.description.data,
                    status=form.status.data,
                )
            except RackRoomNotFoundError as error:
                form.room_id.errors.append(str(error))
            except RackCodeConflictError as error:
                form.code.errors.append(str(error))
            else:
                flash("Rack atualizado com sucesso.", "success")
                return redirect(url_for("rack.detail", rack_id=selected_rack.id))

    return render_template(
        "rack/form.html",
        form=form,
        title="Editar Rack",
        cancel_url=url_for("rack.detail", rack_id=selected_rack.id),
    )


@rack.post("/<int:rack_id>/delete")
@admin_required
def delete(rack_id: int):
    selected_rack = get_rack_or_404(rack_id)
    delete_rack(current_user, selected_rack)
    flash("Rack excluído com sucesso.", "success")
    return redirect(url_for("rack.index"))


@rack.get("/<int:rack_id>/delete-confirm")
@admin_required
def delete_confirm(rack_id: int):
    selected_rack = get_rack_or_404(rack_id)
    return render_template("rack/delete_confirm.html", rack=selected_rack)
