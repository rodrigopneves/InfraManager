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
from sqlalchemy.exc import SQLAlchemyError

from app.audit import record_event
from app.auth import auth
from app.auth.forms import LoginForm, MfaVerifyForm
from app.auth.services import (
    clear_pending_mfa_login,
    consume_totp,
    get_pending_mfa_user,
    start_pending_mfa_login,
    verify_user_password,
)
from app.dashboard.services import (
    get_admin_dashboard_summary,
    get_dashboard_summary,
)
from app.extensions import db, limiter
from app.models import AuditEventType, User, UserRole


@auth.route("/login", methods=["GET", "POST"])
@limiter.limit(
    lambda: current_app.config["AUTH_LOGIN_RATE_LIMIT"], methods=["POST"]
)
def login():
    if current_user.is_authenticated:
        return redirect(url_for("auth.dashboard"))

    form = LoginForm()
    if form.validate_on_submit():
        user = db.session.execute(
            db.select(User).where(User.username == form.username.data)
        ).scalar_one_or_none()

        if verify_user_password(user, form.password.data):
            start_pending_mfa_login(user)
            if user.mfa_enabled:
                if not user.mfa_secret:
                    clear_pending_mfa_login()
                    record_event(
                        AuditEventType.LOGIN_FAILURE,
                        details={"reason": "authentication_failed"},
                    )
                    flash("Usuário ou senha inválidos.", "danger")
                    return render_template("auth/login.html", form=form)
                return redirect(url_for("auth.mfa_verify"))
            return redirect(url_for("account.mfa_setup"))

        clear_pending_mfa_login()
        record_event(
            AuditEventType.LOGIN_FAILURE,
            details={"reason": "authentication_failed"},
        )
        flash("Usuário ou senha inválidos.", "danger")
    elif request.method == "POST":
        clear_pending_mfa_login()
        record_event(
            AuditEventType.LOGIN_FAILURE,
            details={"reason": "authentication_failed"},
        )
        flash("Usuário ou senha inválidos.", "danger")

    return render_template("auth/login.html", form=form)


@auth.route("/mfa/verify", methods=["GET", "POST"])
@limiter.limit(
    lambda: current_app.config["MFA_VERIFY_RATE_LIMIT"], methods=["POST"]
)
def mfa_verify():
    if current_user.is_authenticated:
        clear_pending_mfa_login()
        return redirect(url_for("auth.dashboard"))

    user = get_pending_mfa_user()
    if user is None:
        flash("Sua verificação expirou. Entre novamente.", "danger")
        return redirect(url_for("auth.login"))
    if not user.mfa_enabled or not user.mfa_secret:
        return redirect(url_for("account.mfa_setup"))

    form = MfaVerifyForm()
    if form.validate_on_submit():
        if consume_totp(user, form.code.data):
            try:
                record_event(AuditEventType.MFA_SUCCESS, actor=user, commit=False)
                record_event(AuditEventType.LOGIN_SUCCESS, actor=user, commit=False)
                db.session.commit()
            except SQLAlchemyError:
                db.session.rollback()
                raise
            session.clear()
            login_user(user)
            return redirect(url_for("auth.dashboard"))
        form.code.data = ""
        record_event(AuditEventType.MFA_FAILURE, target=user)
        flash("Código de autenticação inválido.", "danger")
    elif request.method == "POST":
        form.code.data = ""
        record_event(AuditEventType.MFA_FAILURE, target=user)
        flash("Código de autenticação inválido.", "danger")

    return render_template("auth/mfa_verify.html", form=form)


@auth.post("/logout")
@login_required
def logout():
    user = current_user._get_current_object()
    record_event(AuditEventType.LOGOUT, actor=user)
    logout_user()
    session.clear()
    return redirect(url_for("auth.login"))


@auth.get("/dashboard")
@login_required
def dashboard():
    admin_summary = None
    if current_user.has_role(UserRole.ADMIN):
        admin_summary = get_admin_dashboard_summary()

    return render_template(
        "auth/dashboard.html",
        admin_role=UserRole.ADMIN,
        summary=get_dashboard_summary(),
        admin_summary=admin_summary,
    )
