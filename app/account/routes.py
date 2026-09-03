from flask import (
    flash,
    make_response,
    redirect,
    render_template,
    request,
    session,
    url_for,
)
from flask_login import current_user, login_required

from app.account import account
from app.account.forms import DisableMfaForm, MfaCodeForm
from app.account.services import (
    build_mfa_qr_data_uri,
    disable_mfa,
    enable_mfa,
    generate_mfa_secret,
)
from app.audit import record_event
from app.models import AuditEventType


MFA_SETUP_SECRET_KEY = "pending_mfa_setup_secret"


@account.route("/mfa/setup", methods=["GET", "POST"])
@login_required
def mfa_setup():
    if current_user.mfa_enabled:
        session.pop(MFA_SETUP_SECRET_KEY, None)
        flash("MFA já está ativo para sua conta.", "info")
        return redirect(url_for("auth.dashboard"))

    secret = session.get(MFA_SETUP_SECRET_KEY)
    if request.method == "GET" and not secret:
        secret = generate_mfa_secret()
        session[MFA_SETUP_SECRET_KEY] = secret

    if not isinstance(secret, str):
        session.pop(MFA_SETUP_SECRET_KEY, None)
        flash("Inicie novamente a configuração do MFA.", "error")
        return redirect(url_for("account.mfa_setup"))

    form = MfaCodeForm()
    if form.validate_on_submit():
        if enable_mfa(current_user, secret, form.code.data):
            session.pop(MFA_SETUP_SECRET_KEY, None)
            record_event(
                AuditEventType.MFA_ENABLED,
                actor=current_user,
                target=current_user,
            )
            flash("MFA ativado com sucesso.", "success")
            return redirect(url_for("auth.dashboard"))
        form.code.data = ""
        flash("Código de autenticação inválido.", "error")
    elif request.method == "POST":
        form.code.data = ""
        flash("Código de autenticação inválido.", "error")

    qr_data_uri = build_mfa_qr_data_uri(current_user, secret)
    response = make_response(
        render_template(
            "account/mfa_setup.html", form=form, qr_data_uri=qr_data_uri
        )
    )
    response.headers["Cache-Control"] = "no-store"
    return response


@account.post("/mfa/setup/cancel")
@login_required
def cancel_mfa_setup():
    session.pop(MFA_SETUP_SECRET_KEY, None)
    flash("Configuração de MFA cancelada.", "info")
    return redirect(url_for("auth.dashboard"))


@account.route("/mfa/disable", methods=["GET", "POST"])
@login_required
def mfa_disable():
    if not current_user.mfa_enabled or not current_user.mfa_secret:
        flash("MFA não está ativo para sua conta.", "info")
        return redirect(url_for("auth.dashboard"))

    form = DisableMfaForm()
    if form.validate_on_submit():
        if disable_mfa(current_user, form.password.data, form.code.data):
            session.pop(MFA_SETUP_SECRET_KEY, None)
            record_event(
                AuditEventType.MFA_DISABLED,
                actor=current_user,
                target=current_user,
            )
            flash("MFA desativado com sucesso.", "success")
            return redirect(url_for("auth.dashboard"))
        form.code.data = ""
        flash("Não foi possível desativar o MFA.", "error")
    elif request.method == "POST":
        form.code.data = ""
        flash("Não foi possível desativar o MFA.", "error")

    response = make_response(
        render_template("account/mfa_disable.html", form=form)
    )
    response.headers["Cache-Control"] = "no-store"
    return response
