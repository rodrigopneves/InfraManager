from sqlite3 import Connection as SQLiteConnection

from flask_limiter import Limiter
from flask_limiter.util import get_remote_address
from flask_login import LoginManager
from flask_migrate import Migrate
from flask_sqlalchemy import SQLAlchemy
from flask_wtf.csrf import CSRFProtect
from sqlalchemy import event
from sqlalchemy.engine import Engine


@event.listens_for(Engine, "connect")
def configure_sqlite_connection(dbapi_connection, _connection_record) -> None:
    if not isinstance(dbapi_connection, SQLiteConnection):
        return

    cursor = dbapi_connection.cursor()
    try:
        cursor.execute("PRAGMA foreign_keys=ON")
        cursor.execute("PRAGMA busy_timeout=30000")
        cursor.execute("PRAGMA database_list")
        database_path = cursor.fetchone()[2]
        if database_path:
            cursor.execute("PRAGMA journal_mode=WAL")
    finally:
        cursor.close()


db = SQLAlchemy()
migrate = Migrate()
limiter = Limiter(key_func=get_remote_address)
login_manager = LoginManager()
login_manager.login_view = "auth.login"
csrf = CSRFProtect()
