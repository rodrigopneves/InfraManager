import pytest
from sqlalchemy.exc import IntegrityError

from app.extensions import db
from app.models import User, UserRole, validate_email, validate_username


def build_user(username: str, email: str) -> User:
    user = User(username=username, email=email)
    user.set_password("temporary-test-password")
    return user


def test_create_user_and_password_hashing(app) -> None:
    user = build_user("admin.demo", "admin.demo@example.com")
    db.session.add(user)
    db.session.commit()

    stored_user = db.session.get(User, user.id)

    assert stored_user is not None
    assert stored_user.username == "admin.demo"
    assert stored_user.email == "admin.demo@example.com"
    assert stored_user.password_hash != "temporary-test-password"
    assert stored_user.check_password("temporary-test-password") is True
    assert stored_user.check_password("incorrect-password") is False
    assert stored_user.is_active is True
    assert stored_user.role == UserRole.VIEWER.value
    assert stored_user.created_at is not None
    assert stored_user.updated_at is not None


def test_updated_at_changes_when_user_is_updated(app) -> None:
    user = build_user("viewer.demo", "viewer.demo@example.com")
    db.session.add(user)
    db.session.commit()
    original_updated_at = user.updated_at

    user.email = "viewer.updated@example.com"
    db.session.commit()

    assert user.updated_at > original_updated_at


def test_username_must_be_unique(app) -> None:
    db.session.add(build_user("operator.demo", "first@example.com"))
    db.session.commit()
    db.session.add(build_user("operator.demo", "second@example.com"))

    with pytest.raises(IntegrityError):
        db.session.commit()

    db.session.rollback()


def test_email_must_be_unique(app) -> None:
    db.session.add(build_user("first.demo", "shared@example.com"))
    db.session.commit()
    db.session.add(build_user("second.demo", "shared@example.com"))

    with pytest.raises(IntegrityError):
        db.session.commit()

    db.session.rollback()


@pytest.mark.parametrize(
    "username",
    ["ab", "user name", "user@example", "user/name"],
)
def test_invalid_username_is_rejected(username: str) -> None:
    with pytest.raises(ValueError):
        validate_username(username)


def test_username_and_email_are_normalized() -> None:
    user = User(
        username="  Demo.User  ",
        email="  Demo.User@Example.COM  ",
    )

    assert user.username == "demo.user"
    assert user.email == "demo.user@example.com"
    assert validate_email("  Another.User@Example.COM ") == (
        "another.user@example.com"
    )


@pytest.mark.parametrize("email", ["invalid", "missing@domain", "two@@example.com"])
def test_invalid_email_is_rejected(email: str) -> None:
    with pytest.raises(ValueError):
        validate_email(email)


def test_invalid_role_is_rejected() -> None:
    with pytest.raises(ValueError):
        User(
            username="invalid.role",
            email="invalid.role@example.com",
            role="superadmin",
        )
