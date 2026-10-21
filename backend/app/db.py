from sqlalchemy import create_engine, make_url
from sqlalchemy.orm import DeclarativeBase, sessionmaker

from .config import DATABASE_URL


def connect_args(url: str) -> dict:
    # psycopg 3 prepares statements it runs repeatedly, and prepared statements
    # can collide behind a transaction-mode pooler (Neon's "-pooler" hosts are
    # PgBouncer). Turn that off for pooled connections only.
    host = make_url(url).host or ""
    return {"prepare_threshold": None} if "-pooler" in host else {}


# pool_pre_ping also covers Neon scaling an idle database to zero.
engine = create_engine(DATABASE_URL, pool_pre_ping=True, connect_args=connect_args(DATABASE_URL))
SessionLocal = sessionmaker(bind=engine, autoflush=False, expire_on_commit=False)


class Base(DeclarativeBase):
    pass


def get_db():
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()


def get_session_factory() -> sessionmaker:
    """For background tasks, which outlive the request's own session."""
    return SessionLocal
