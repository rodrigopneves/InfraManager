from flask import flash, redirect, render_template, url_for
from flask_login import current_user, login_required, login_user, logout_user

from app.auth import auth
from app.auth.forms import LoginForm
from app.extensions import db
from app.models import User


@auth.route("/login", methods=["GET", "POST"])
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

    return render_template("auth/login.html", form=form)


@auth.post("/logout")
@login_required
def logout():
    logout_user()
    return redirect(url_for("auth.login"))


@auth.get("/dashboard")
@login_required
def dashboard():
    return render_template("auth/dashboard.html")
