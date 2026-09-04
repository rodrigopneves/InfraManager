from flask import flash, redirect, render_template, request, url_for
from flask_login import current_user
from sqlalchemy.orm import selectinload

from app.admin import admin
from app.admin.decorators import admin_required
from app.admin.forms import CreateUserForm, EditUserForm
from app.admin.services import (
    AdminOperationError,
    add_identity_conflict_errors,
    create_user,
    toggle_user_active,
    update_user,
)
from app.audit.services import format_details
from app.extensions import db
from app.models import AuditLog, User


AUDIT_LOGS_PER_PAGE = 20


@admin.get("/users")
@admin_required
def users():
    registered_users = db.session.scalars(
        db.select(User).order_by(User.username)
    ).all()
    return render_template("admin/users.html", users=registered_users)


@admin.get("/audit")
@admin_required
def audit():
    page = request.args.get("page", 1, type=int)
    query = (
        db.select(AuditLog)
        .options(selectinload(AuditLog.actor), selectinload(AuditLog.target))
        .order_by(
            AuditLog.created_at.desc(),
            AuditLog.id.desc(),
        )
    )
    pagination = db.paginate(
        query,
        page=page,
        per_page=AUDIT_LOGS_PER_PAGE,
        error_out=True,
    )
    entries = [
        {"log": audit_log, "details": format_details(audit_log.details)}
        for audit_log in pagination.items
    ]
    return render_template(
        "admin/audit.html", entries=entries, pagination=pagination
    )


@admin.route("/users/new", methods=["GET", "POST"])
@admin_required
def new_user():
    form = CreateUserForm()
    if form.validate_on_submit() and not add_identity_conflict_errors(form):
        create_user(
            username=form.username.data,
            email=form.email.data,
            password=form.password.data,
            is_active=form.is_active.data,
            role=form.role.data,
            actor=current_user,
        )
        flash("Usuário criado com sucesso.", "success")
        return redirect(url_for("admin.users"))
    return render_template("admin/user_form.html", form=form, title="Novo usuário")


@admin.route("/users/<int:user_id>/edit", methods=["GET", "POST"])
@admin_required
def edit_user(user_id: int):
    user = db.get_or_404(User, user_id)
    form = EditUserForm(obj=user)
    if form.validate_on_submit() and not add_identity_conflict_errors(
        form, exclude_user_id=user.id
    ):
        try:
            update_user(
                current_user,
                user,
                username=form.username.data,
                email=form.email.data,
                is_active=form.is_active.data,
                role=form.role.data,
            )
        except AdminOperationError as error:
            flash(str(error), "warning")
        else:
            flash("Usuário atualizado com sucesso.", "success")
            return redirect(url_for("admin.users"))
    return render_template("admin/user_form.html", form=form, title="Editar usuário")


@admin.post("/users/<int:user_id>/toggle-active")
@admin_required
def toggle_active(user_id: int):
    user = db.get_or_404(User, user_id)
    try:
        toggle_user_active(current_user, user)
    except AdminOperationError as error:
        flash(str(error), "warning")
    else:
        status = "ativado" if user.is_active else "desativado"
        flash(f"Usuário {status} com sucesso.", "success")
    return redirect(url_for("admin.users"))
