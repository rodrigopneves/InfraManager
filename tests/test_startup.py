from flask import Flask


def test_wsgi_exports_flask_application() -> None:
    from wsgi import app

    assert isinstance(app, Flask)
    assert app.view_functions["main.health"] is not None
