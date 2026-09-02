from flask import Blueprint, render_template


main = Blueprint("main", __name__)


@main.get("/")
def index() -> str:
    return render_template("base.html")
