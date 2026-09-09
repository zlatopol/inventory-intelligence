from collections.abc import Iterator

from sqlalchemy import create_engine
from sqlalchemy.orm import DeclarativeBase, Session, sessionmaker

from app.shared.config import get_settings


class Base(DeclarativeBase):
    """Declarative base for all domain models."""


_engine = None
_session_factory: sessionmaker[Session] | None = None


def get_engine():
    global _engine, _session_factory
    if _engine is None:
        _engine = create_engine(get_settings().database_url, pool_pre_ping=True)
        _session_factory = sessionmaker(bind=_engine, expire_on_commit=False)
    return _engine


def get_session() -> Iterator[Session]:
    """FastAPI dependency: one session per request.

    The session is the transaction scope; committing is owned by services
    (ADR-0003), not by this dependency.
    """
    get_engine()
    with _session_factory() as session:
        yield session
