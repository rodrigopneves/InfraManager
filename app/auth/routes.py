from flask import current_app, flash, redirect, render_template, request, url_for
from flask_login import current_user, login_required, login_user, logout_user

from app.auth import auth
from app.auth.forms import LoginForm
from app.extensions import db, limiter
from app.models import User, UserRole


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

        if user is not None and user.is_active and user.check_password(
            form.password.data
        ):
            login_user(user)
            return redirect(url_for("auth.dashboard"))

        flash("Usuário ou senha inválidos.", "error")
    elif request.method == "POST":
        flash("Usuário ou senha inválidos.", "error")

    return render_template("auth/login.html", form=form)


@auth.post("/logout")
@login_required
def logout():
    logout_user()
    return redirect(url_for("auth.login"))


@auth.get("/dashboard")
@login_required
def dashboard():
    return render_template("auth/dashboard.html", admin_role=UserRole.ADMIN)
