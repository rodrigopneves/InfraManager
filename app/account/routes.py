from flask import (
    current_app,
    flash,
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
from app.extensions import limiter
from app.models import (
    AuditEventType,
    SecurityAlertSeverity,
    SecurityAlertType,
)
from app.security_alerts import record_security_event


MFA_SETUP_SECRET_KEY = "pending_mfa_setup_secret"


@account.route("/mfa/setup", methods=["GET", "POST"])
@login_required
@limiter.limit(
    lambda: current_app.config["MFA_SETUP_RATE_LIMIT"], methods=["POST"]
)
def mfa_setup():
    if current_user.mfa_enabled:
        session.pop(MFA_SETUP_SECRET_KEY, None)
        return redirect(url_for("auth.dashboard"))

    user = current_user._get_current_object()

    secret = session.get(MFA_SETUP_SECRET_KEY)
    if request.method == "GET" and not secret:
        secret = generate_mfa_secret()
        session[MFA_SETUP_SECRET_KEY] = secret

    if not isinstance(secret, str):
        session.pop(MFA_SETUP_SECRET_KEY, None)
        flash("Inicie novamente a configuração do MFA.", "danger")
        return redirect(url_for("account.mfa_setup"))

    form = MfaCodeForm()
    if form.validate_on_submit():
        if enable_mfa(user, secret, form.code.data):
            session.pop(MFA_SETUP_SECRET_KEY, None)
            flash("MFA ativado com sucesso.", "success")
            return redirect(url_for("auth.dashboard"))
        form.code.data = ""
        record_event(AuditEventType.MFA_FAILURE, target=user)
        record_security_event(
            SecurityAlertType.MFA_FAILURE,
            SecurityAlertSeverity.WARNING,
            user=user,
        )
        flash("Código de autenticação inválido.", "danger")
    elif request.method == "POST":
        form.code.data = ""
        record_event(AuditEventType.MFA_FAILURE, target=user)
        record_security_event(
            SecurityAlertType.MFA_FAILURE,
            SecurityAlertSeverity.WARNING,
            user=user,
        )
        flash("Código de autenticação inválido.", "danger")

    qr_data_uri = build_mfa_qr_data_uri(user, secret)
    return render_template(
        "account/mfa_setup.html", form=form, qr_data_uri=qr_data_uri
    )


@account.post("/mfa/setup/cancel")
@login_required
def cancel_mfa_setup():
    session.pop(MFA_SETUP_SECRET_KEY, None)
    flash("Configuração de MFA cancelada.", "info")
    return redirect(url_for("auth.dashboard"))


@account.route("/mfa/disable", methods=["GET", "POST"])
@login_required
@limiter.limit(
    lambda: current_app.config["MFA_DISABLE_RATE_LIMIT"], methods=["POST"]
)
def mfa_disable():
    if not current_user.mfa_enabled or not current_user.mfa_secret:
        flash("MFA não está ativo para sua conta.", "info")
        return redirect(url_for("auth.dashboard"))

    form = DisableMfaForm()
    if form.validate_on_submit():
        if disable_mfa(current_user, form.password.data, form.code.data):
            flash("MFA desativado com sucesso.", "success")
            return redirect(url_for("auth.dashboard"))
        form.code.data = ""
        user = current_user._get_current_object()
        record_event(AuditEventType.MFA_FAILURE, target=user)
        record_security_event(
            SecurityAlertType.MFA_FAILURE,
            SecurityAlertSeverity.WARNING,
            user=user,
        )
        flash("Não foi possível desativar o MFA.", "danger")
    elif request.method == "POST":
        form.code.data = ""
        user = current_user._get_current_object()
        record_event(AuditEventType.MFA_FAILURE, target=user)
        record_security_event(
            SecurityAlertType.MFA_FAILURE,
            SecurityAlertSeverity.WARNING,
            user=user,
        )
        flash("Não foi possível desativar o MFA.", "danger")

    return render_template("account/mfa_disable.html", form=form)
