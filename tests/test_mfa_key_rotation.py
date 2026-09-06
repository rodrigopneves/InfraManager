from cryptography.fernet import Fernet
import pyotp
import pytest
from sqlalchemy.exc import SQLAlchemyError

from app.extensions import db
from app.models import User


def raw_mfa_secrets() -> dict[str, str | None]:
    return dict(
        db.session.execute(db.select(User.username, User._mfa_secret)).all()
    )


def invoke_rotation(app, old_key: str, new_key: str):
    return app.test_cli_runner().invoke(
        args=["rotate-mfa-key"],
        input=f"{old_key}\n{new_key}\n{new_key}\n",
    )


def add_mfa_user(username: str, secret: str) -> User:
    user = User(username=username, email=f"{username}@example.com")
    user.set_password("valid-test-password")
    user.mfa_secret = secret
    user.mfa_enabled = True
    db.session.add(user)
    return user


def test_rotate_mfa_key_updates_multiple_users_and_preserves_plaintexts(app) -> None:
    old_key = app.config["MFA_ENCRYPTION_KEY"]
    new_key = Fernet.generate_key().decode("ascii")
    first_secret = pyotp.random_base32()
    second_secret = pyotp.random_base32()
    add_mfa_user("rotation.one", first_secret)
    add_mfa_user("rotation.two", second_secret)
    without_mfa = User(username="rotation.none", email="rotation.none@example.com")
    without_mfa.set_password("valid-test-password")
    db.session.add(without_mfa)
    db.session.commit()
    before = raw_mfa_secrets()

    result = invoke_rotation(app, old_key, new_key)
    after = raw_mfa_secrets()

    assert result.exit_code == 0
    assert "Segredos MFA rotacionados: 2." in result.output
    assert before["rotation.one"] != after["rotation.one"]
    assert before["rotation.two"] != after["rotation.two"]
    assert after["rotation.none"] is None
    assert old_key not in result.output
    assert new_key not in result.output

    app.config["MFA_ENCRYPTION_KEY"] = new_key
    db.session.expire_all()
    users = {
        user.username: user
        for user in db.session.scalars(
            db.select(User).where(User.username.in_(["rotation.one", "rotation.two"]))
        )
    }
    assert users["rotation.one"].mfa_secret == first_secret
    assert users["rotation.two"].mfa_secret == second_secret


def test_rotate_mfa_key_rejects_wrong_old_key_without_changes(app) -> None:
    secret = pyotp.random_base32()
    add_mfa_user("rotation.wrong", secret)
    db.session.commit()
    before = raw_mfa_secrets()
    wrong_key = Fernet.generate_key().decode("ascii")
    new_key = Fernet.generate_key().decode("ascii")

    result = invoke_rotation(app, wrong_key, new_key)

    assert result.exit_code != 0
    assert "Não foi possível rotacionar" in result.output
    assert raw_mfa_secrets() == before
    assert secret not in result.output
    assert wrong_key not in result.output
    assert new_key not in result.output


def test_rotate_mfa_key_rejects_invalid_new_key_before_changes(app) -> None:
    old_key = app.config["MFA_ENCRYPTION_KEY"]
    secret = pyotp.random_base32()
    add_mfa_user("rotation.invalid", secret)
    db.session.commit()
    before = raw_mfa_secrets()

    result = invoke_rotation(app, old_key, "invalid-new-key")

    assert result.exit_code != 0
    assert "Chave Fernet inválida." in result.output
    assert raw_mfa_secrets() == before
    assert old_key not in result.output
    assert "invalid-new-key" not in result.output


def test_rotate_mfa_key_rolls_back_every_user_on_commit_failure(
    app,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    old_key = app.config["MFA_ENCRYPTION_KEY"]
    new_key = Fernet.generate_key().decode("ascii")
    add_mfa_user("rotation.rollback-one", pyotp.random_base32())
    add_mfa_user("rotation.rollback-two", pyotp.random_base32())
    db.session.commit()
    before = raw_mfa_secrets()

    def fail_commit() -> None:
        raise SQLAlchemyError("commit failed")

    monkeypatch.setattr(db.session, "commit", fail_commit)
    result = invoke_rotation(app, old_key, new_key)

    assert result.exit_code != 0
    assert "Não foi possível rotacionar" in result.output
    assert raw_mfa_secrets() == before


def test_rotate_mfa_key_requires_legacy_migration_first(app) -> None:
    old_key = app.config["MFA_ENCRYPTION_KEY"]
    new_key = Fernet.generate_key().decode("ascii")
    user = User(username="rotation.legacy", email="rotation.legacy@example.com")
    user.set_password("valid-test-password")
    db.session.add(user)
    db.session.flush()
    db.session.execute(
        User.__table__.update()
        .where(User.id == user.id)
        .values(mfa_secret=pyotp.random_base32(), mfa_enabled=True)
    )
    db.session.commit()
    before = raw_mfa_secrets()

    result = invoke_rotation(app, old_key, new_key)

    assert result.exit_code != 0
    assert "execute encrypt-mfa-secrets antes" in result.output
    assert raw_mfa_secrets() == before
