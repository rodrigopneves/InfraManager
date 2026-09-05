from flask import (
    current_app,
    flash,
    redirect,
    render_template,
    request,
    session,
    url_for,
)
from flask_login import current_user, login_required, login_user, logout_user

from app.account import account
from app.account.forms import DisableMfaForm, MfaCodeForm
from app.account.services import (
    build_mfa_qr_data_uri,
    disable_mfa,
    enable_mfa,
    generate_mfa_secret,
)
from app.auth.services import get_pending_mfa_user, start_pending_mfa_login
from app.extensions import limiter


MFA_SETUP_SECRET_KEY = "pending_mfa_setup_secret"


@account.route("/mfa/setup", methods=["GET", "POST"])
@limiter.limit(
    lambda: current_app.config["MFA_SETUP_RATE_LIMIT"], methods=["POST"]
)
def mfa_setup():
    if current_user.is_authenticated:
        session.pop(MFA_SETUP_SECRET_KEY, None)
        return redirect(url_for("auth.dashboard"))

    user = get_pending_mfa_user()
    if user is None:
        flash("Sua configuração expirou. Entre novamente.", "danger")
        return redirect(url_for("auth.login"))
    if user.mfa_enabled:
        return redirect(url_for("auth.mfa_verify"))

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
            session.clear()
            login_user(user)
            flash("MFA ativado com sucesso.", "success")
            return redirect(url_for("auth.dashboard"))
        form.code.data = ""
        flash("Código de autenticação inválido.", "danger")
    elif request.method == "POST":
        form.code.data = ""
        flash("Código de autenticação inválido.", "danger")

    qr_data_uri = build_mfa_qr_data_uri(user, secret)
    return render_template(
        "account/mfa_setup.html", form=form, qr_data_uri=qr_data_uri
    )


@account.post("/mfa/setup/cancel")
def cancel_mfa_setup():
    if current_user.is_authenticated:
        return redirect(url_for("auth.dashboard"))
    session.clear()
    flash("Configuração de MFA cancelada.", "info")
    return redirect(url_for("auth.login"))


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
            user = current_user._get_current_object()
            logout_user()
            start_pending_mfa_login(user)
            flash("Configure novamente o MFA para continuar.", "success")
            return redirect(url_for("account.mfa_setup"))
        form.code.data = ""
        flash("Não foi possível desativar o MFA.", "danger")
    elif request.method == "POST":
        form.code.data = ""
        flash("Não foi possível desativar o MFA.", "danger")

    return render_template("account/mfa_disable.html", form=form)
