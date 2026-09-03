from app.extensions import db
from app.models import User, UserRole


class AdminOperationError(ValueError):
    pass


def add_identity_conflict_errors(
    form, *, exclude_user_id: int | None = None
) -> bool:
    username_query = db.select(User).where(User.username == form.username.data)
    email_query = db.select(User).where(User.email == form.email.data)
    if exclude_user_id is not None:
        username_query = username_query.where(User.id != exclude_user_id)
        email_query = email_query.where(User.id != exclude_user_id)

    has_conflict = False
    if db.session.scalar(username_query) is not None:
        form.username.errors.append("Este nome de usuário já está em uso.")
        has_conflict = True
    if db.session.scalar(email_query) is not None:
        form.email.errors.append("Este e-mail já está em uso.")
        has_conflict = True
    return has_conflict


def create_user(
    *, username: str, email: str, password: str, is_active: bool, role: str
) -> User:
    user = User(
        username=username,
        email=email,
        is_active=is_active,
        role=role,
    )
    user.set_password(password)
    db.session.add(user)
    db.session.commit()
    return user


def update_user(
    actor: User,
    user: User,
    *,
    username: str,
    email: str,
    is_active: bool,
    role: str,
) -> None:
    ensure_admin_access_remains(actor, user, is_active=is_active, role=role)
    user.username = username
    user.email = email
    user.is_active = is_active
    user.role = role
    db.session.commit()


def toggle_user_active(actor: User, user: User) -> None:
    new_status = not user.is_active
    ensure_admin_access_remains(actor, user, is_active=new_status, role=user.role)
    user.is_active = new_status
    db.session.commit()


def ensure_admin_access_remains(
    actor: User, user: User, *, is_active: bool, role: str
) -> None:
    if user.id == actor.id and user.is_active and not is_active:
        raise AdminOperationError("Você não pode desativar sua própria conta.")
    if (
        user.id == actor.id
        and user.has_role(UserRole.ADMIN)
        and role != UserRole.ADMIN.value
    ):
        raise AdminOperationError(
            "Você não pode remover seu próprio acesso administrativo."
        )

    removes_active_admin = user.is_active and user.has_role(UserRole.ADMIN) and (
        not is_active or role != UserRole.ADMIN.value
    )
    if removes_active_admin and active_admin_count() <= 1:
        raise AdminOperationError(
            "O último administrador ativo não pode ser desativado ou rebaixado."
        )


def active_admin_count() -> int:
    query = db.select(db.func.count()).select_from(User).where(
        User.role == UserRole.ADMIN.value, User.is_active.is_(True)
    )
    return db.session.scalar(query) or 0
