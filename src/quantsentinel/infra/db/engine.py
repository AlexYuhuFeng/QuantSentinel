"""
Database engine + session utilities.

Goals:
- SQLAlchemy 2.0 style
- Lazy engine creation (no connection on import)
- One engine per process
- Standard session_scope() transaction boundary
"""

from __future__ import annotations

from contextlib import contextmanager
from typing import Any, Generator

from sqlalchemy import text
from sqlalchemy.engine import Engine
from sqlalchemy.orm import Session, sessionmaker

from quantsentinel.common.config import get_settings

_ENGINE: Engine | None = None
_SESSIONMAKER: sessionmaker[Session] | None = None


def get_engine() -> Engine:
    global _ENGINE, _SESSIONMAKER

    if _ENGINE is not None and _SESSIONMAKER is not None:
        return _ENGINE

    settings = get_settings()
    if not settings.database_url:
        raise RuntimeError("DATABASE_URL is not configured")

    from sqlalchemy import create_engine

    _ENGINE = create_engine(
        settings.database_url,
        future=True,
        pool_pre_ping=True,
        pool_size=settings.db_pool_size,
        max_overflow=settings.db_max_overflow,
        pool_timeout=settings.db_pool_timeout,
    )

    _SESSIONMAKER = sessionmaker(bind=_ENGINE, class_=Session, autoflush=False, autocommit=False, future=True)
    return _ENGINE


def get_sessionmaker() -> sessionmaker[Session]:
    global _SESSIONMAKER
    if _SESSIONMAKER is None:
        _ = get_engine()
    assert _SESSIONMAKER is not None
    return _SESSIONMAKER


@contextmanager
def session_scope() -> Generator[Session, None, None]:
    """
    Transaction boundary:
      - commit on success
      - rollback on error
      - always close
    """
    SessionLocal = get_sessionmaker()
    session = SessionLocal()
    try:
        yield session
        session.commit()
    except Exception:
        session.rollback()
        raise
    finally:
        session.close()


def db_healthcheck() -> dict[str, Any]:
    """
    Returns:
      {"status": "ok"} or {"status": "error", "detail": "..."}
    """
    try:
        engine = get_engine()
        with engine.connect() as conn:
            conn.execute(text("SELECT 1"))
        return {"status": "ok"}
    except Exception as e:
        return {"status": "error", "detail": str(e)}