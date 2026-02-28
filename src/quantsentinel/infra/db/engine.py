"""
Database engine & session management (SQLAlchemy 2.0).

Design goals:
- Single source of truth for Engine + Session factory
- No side effects on import (no immediate DB connections)
- Safe for multi-process (web/worker/beat) deployment
"""

from __future__ import annotations

from contextlib import contextmanager
from typing import Iterator

from sqlalchemy import Engine, text
from sqlalchemy.engine import create_engine as sa_create_engine
from sqlalchemy.exc import SQLAlchemyError
from sqlalchemy.orm import Session, sessionmaker

from quantsentinel.common.config import get_settings


def create_engine(url: str) -> Engine:
    """
    Create a SQLAlchemy Engine.

    Args:
        url: SQLAlchemy database URL (e.g., postgresql+psycopg://...)

    Returns:
        SQLAlchemy Engine instance.
    """
    # Notes:
    # - pool_pre_ping avoids stale connections (important in containers)
    # - pool_recycle avoids long-lived connections across network changes
    return sa_create_engine(
        url,
        future=True,
        pool_pre_ping=True,
        pool_recycle=1800,
        pool_size=5,
        max_overflow=10,
    )


def get_engine() -> Engine:
    """
    Lazily create and return the application Engine.
    """
    settings = get_settings()
    return create_engine(settings.database_url)


def get_session_factory() -> sessionmaker[Session]:
    """
    Create a configured sessionmaker bound to the application engine.
    """
    engine = get_engine()
    return sessionmaker(bind=engine, autoflush=False, autocommit=False, future=True)


@contextmanager
def session_scope() -> Iterator[Session]:
    """
    Provide a transactional scope around a series of operations.

    Usage:
        with session_scope() as session:
            session.add(...)
            ...

    Commits on success, rollbacks on exception.
    """
    SessionLocal = get_session_factory()
    session = SessionLocal()
    try:
        yield session
        session.commit()
    except Exception:
        session.rollback()
        raise
    finally:
        session.close()


def db_healthcheck() -> dict[str, str]:
    """
    Lightweight DB health check.

    Returns:
        {"status": "ok"} on success, or {"status": "error", "detail": "..."} on failure.
    """
    try:
        engine = get_engine()
        with engine.connect() as conn:
            conn.execute(text("SELECT 1"))
        return {"status": "ok"}
    except SQLAlchemyError as e:
        return {"status": "error", "detail": str(e)}