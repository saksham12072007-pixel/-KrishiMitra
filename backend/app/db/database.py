from sqlalchemy import create_engine, event
from sqlalchemy.orm import DeclarativeBase, sessionmaker

from app.core.config import get_settings

settings = get_settings()


class Base(DeclarativeBase):
    pass


def _normalize_database_url(url: str) -> str:
    """
    Managed Postgres providers (Render, Railway, etc.) hand out plain
    postgres:// / postgresql:// URLs, which default to the psycopg2 dialect --
    not installed here (this project uses psycopg v3). Rewrite to the
    explicit psycopg dialect so those connection strings work unmodified.
    """
    if url.startswith("postgres://"):
        return "postgresql+psycopg://" + url[len("postgres://"):]
    if url.startswith("postgresql://"):
        return "postgresql+psycopg://" + url[len("postgresql://"):]
    return url


database_url = _normalize_database_url(settings.database_url)
is_sqlite = database_url.startswith("sqlite")
connect_args = (
    {"check_same_thread": False, "timeout": 30}
    if is_sqlite
    else {}
)
engine = create_engine(database_url, connect_args=connect_args, future=True)
SessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine, future=True)


if is_sqlite:
    @event.listens_for(engine, "connect")
    def configure_sqlite_connection(dbapi_connection, _connection_record):
        cursor = dbapi_connection.cursor()
        cursor.execute("PRAGMA busy_timeout=30000")
        cursor.execute("PRAGMA journal_mode=WAL")
        cursor.close()


def get_db():
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()
