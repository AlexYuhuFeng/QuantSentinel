"""
Users repository (CRUD + queries only).

Rules:
- No business logic (no password hashing, no RBAC decisions)
- No Streamlit/Celery imports
- Session is injected by caller (services layer controls transactions)
"""

from __future__ import annotations

import uuid
from dataclasses import dataclass
from datetime import datetime
from typing import Iterable

from sqlalchemy import select, update
from sqlalchemy.orm import Session

from quantsentinel.infra.db.models import User, UserRole


@dataclass(frozen=True)
class UserCreate:
    """
    Input DTO for creating a user.
    Password must already be hashed by the caller (services/security layer).
    """
    username: str
    email: str
    password_hash: str
    role: UserRole
    default_language: str = "en"
    is_active: bool = True


class UsersRepo:
    """Repository for User entities."""

    def __init__(self, session: Session) -> None:
        self._session = session

    # -----------------------------
    # Read
    # -----------------------------

    def get(self, user_id: uuid.UUID) -> User | None:
        return self._session.get(User, user_id)

    def get_by_username(self, username: str) -> User | None:
        stmt = select(User).where(User.username == username)
        return self._session.execute(stmt).scalar_one_or_none()

    def get_by_email(self, email: str) -> User | None:
        stmt = select(User).where(User.email == email)
        return self._session.execute(stmt).scalar_one_or_none()

    def list_users(self, *, limit: int = 200, offset: int = 0) -> list[User]:
        stmt = select(User).order_by(User.created_at.desc()).limit(limit).offset(offset)
        return list(self._session.execute(stmt).scalars().all())

    def count_users(self) -> int:
        # Avoid importing func here to keep it simple; count via iteration is not acceptable.
        # We'll use a tiny select count for correctness.
        from sqlalchemy import func  # local import OK in repo
        stmt = select(func.count()).select_from(User)
        return int(self._session.execute(stmt).scalar_one())

    # -----------------------------
    # Create
    # -----------------------------

    def create(self, data: UserCreate) -> User:
        user = User(
            id=uuid.uuid4(),
            username=data.username,
            email=data.email,
            password_hash=data.password_hash,
            role=data.role,
            default_language=data.default_language,
            is_active=data.is_active,
        )
        self._session.add(user)
        # Flush to surface DB constraint issues (unique username/email) early.
        self._session.flush()
        return user

    # -----------------------------
    # Update
    # -----------------------------

    def set_last_login(self, user_id: uuid.UUID, ts: datetime) -> None:
        stmt = update(User).where(User.id == user_id).values(last_login=ts)
        self._session.execute(stmt)

    def set_active(self, user_id: uuid.UUID, is_active: bool) -> None:
        stmt = update(User).where(User.id == user_id).values(is_active=is_active)
        self._session.execute(stmt)

    def set_role(self, user_id: uuid.UUID, role: UserRole) -> None:
        stmt = update(User).where(User.id == user_id).values(role=role)
        self._session.execute(stmt)

    def set_default_language(self, user_id: uuid.UUID, language: str) -> None:
        stmt = update(User).where(User.id == user_id).values(default_language=language)
        self._session.execute(stmt)

    def set_password_hash(self, user_id: uuid.UUID, password_hash: str) -> None:
        stmt = update(User).where(User.id == user_id).values(password_hash=password_hash)
        self._session.execute(stmt)

    # -----------------------------
    # Bulk helpers (optional)
    # -----------------------------

    def ensure_admin_exists(self) -> User | None:
        """
        Repo-level convenience: returns an existing Admin user if present, else None.
        Creation of default admin is a service responsibility.
        """
        stmt = select(User).where(User.role == UserRole.ADMIN).limit(1)
        return self._session.execute(stmt).scalar_one_or_none()