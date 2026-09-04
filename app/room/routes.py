from flask import flash, redirect, render_template, request, url_for
from flask_login import current_user

from app.admin.decorators import admin_required, roles_required
from app.models import UserRole
from app.room import room
from app.room.forms import RoomForm
from app.room.services import (
    RoomCodeConflictError,
    RoomDatacenterNotFoundError,
    RoomHasRacksError,
    create_room,
    delete_room,
    get_room_or_404,
    list_datacenters_for_form,
    list_rooms,
    room_code_exists,
    update_room,
)


read_access_required = roles_required(
    UserRole.ADMIN, UserRole.OPERATOR, UserRole.VIEWER
)


def _set_datacenter_choices(form: RoomForm) -> set[int]:
    datacenters = list_datacenters_for_form()
    form.datacenter_id.choices = [
        (datacenter.id, f"{datacenter.code} — {datacenter.name}")
        for datacenter in datacenters
    ]
    return {datacenter.id for datacenter in datacenters}


@room.get("")
@read_access_required
def index():
    page = request.args.get("page", 1, type=int)
    pagination = list_rooms(page)
    return render_template(
        "room/index.html",
        pagination=pagination,
        admin_role=UserRole.ADMIN,
    )


@room.get("/<int:room_id>")
@read_access_required
def detail(room_id: int):
    selected_room = get_room_or_404(room_id)
    return render_template(
        "room/detail.html",
        room=selected_room,
        admin_role=UserRole.ADMIN,
    )


@room.route("/create", methods=["GET", "POST"])
@admin_required
def create():
    form = RoomForm()
    valid_datacenter_ids = _set_datacenter_choices(form)
    if request.method == "GET":
        requested_datacenter_id = request.args.get("datacenter_id", type=int)
        if requested_datacenter_id in valid_datacenter_ids:
            form.datacenter_id.data = requested_datacenter_id

    if form.validate_on_submit():
        if room_code_exists(form.datacenter_id.data, form.code.data):
            form.code.errors.append(
                "Já existe uma Sala com este código no Datacenter selecionado."
            )
        else:
            try:
                created_room = create_room(
                    current_user,
                    datacenter_id=form.datacenter_id.data,
                    name=form.name.data,
                    code=form.code.data,
                    description=form.description.data,
                    status=form.status.data,
                )
            except RoomDatacenterNotFoundError as error:
                form.datacenter_id.errors.append(str(error))
            except RoomCodeConflictError as error:
                form.code.errors.append(str(error))
            else:
                flash("Sala criada com sucesso.", "success")
                return redirect(url_for("room.detail", room_id=created_room.id))

    return render_template(
        "room/form.html",
        form=form,
        title="Nova Sala",
        cancel_url=url_for("room.index"),
    )


@room.route("/<int:room_id>/edit", methods=["GET", "POST"])
@admin_required
def edit(room_id: int):
    selected_room = get_room_or_404(room_id)
    form = RoomForm(obj=selected_room)
    _set_datacenter_choices(form)

    if form.validate_on_submit():
        if room_code_exists(
            form.datacenter_id.data,
            form.code.data,
            exclude_room_id=selected_room.id,
        ):
            form.code.errors.append(
                "Já existe uma Sala com este código no Datacenter selecionado."
            )
        else:
            try:
                update_room(
                    current_user,
                    selected_room,
                    datacenter_id=form.datacenter_id.data,
                    name=form.name.data,
                    code=form.code.data,
                    description=form.description.data,
                    status=form.status.data,
                )
            except RoomDatacenterNotFoundError as error:
                form.datacenter_id.errors.append(str(error))
            except RoomCodeConflictError as error:
                form.code.errors.append(str(error))
            else:
                flash("Sala atualizada com sucesso.", "success")
                return redirect(
                    url_for("room.detail", room_id=selected_room.id)
                )

    return render_template(
        "room/form.html",
        form=form,
        title="Editar Sala",
        cancel_url=url_for("room.detail", room_id=selected_room.id),
    )


@room.post("/<int:room_id>/delete")
@admin_required
def delete(room_id: int):
    selected_room = get_room_or_404(room_id)
    try:
        delete_room(current_user, selected_room)
    except RoomHasRacksError as error:
        flash(str(error), "warning")
        return redirect(url_for("room.detail", room_id=selected_room.id))
    flash("Sala excluída com sucesso.", "success")
    return redirect(url_for("room.index"))


@room.get("/<int:room_id>/delete-confirm")
@admin_required
def delete_confirm(room_id: int):
    selected_room = get_room_or_404(room_id)
    return render_template("room/delete_confirm.html", room=selected_room)
