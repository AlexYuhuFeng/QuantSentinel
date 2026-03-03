from __future__ import annotations

import uuid
from contextlib import contextmanager
from dataclasses import dataclass
from datetime import datetime

from quantsentinel.infra.db.models import UserRole
from quantsentinel.services.auth_service import AuthService


@dataclass
class _FakeUser:
    id: uuid.UUID
    username: str
    email: str
    password_hash: str
    role: UserRole
    default_language: str
    is_active: bool
    last_login: datetime | None = None


class _FakeUsersRepo:
    def __init__(self, session) -> None:
        self._store = session

    def count_users(self) -> int:
        return len(self._store["users"])

    def ensure_admin_exists(self) -> _FakeUser | None:
        for user in self._store["users"]:
            if user.role == UserRole.ADMIN:
                return user
        return None

    def create(self, data) -> _FakeUser:
        user = _FakeUser(
            id=uuid.uuid4(),
            username=data.username,
            email=data.email,
            password_hash=data.password_hash,
            role=data.role,
            default_language=data.default_language,
            is_active=data.is_active,
        )
        self._store["users"].append(user)
        return user

    def get_by_email(self, email: str) -> _FakeUser | None:
        for user in self._store["users"]:
            if user.email == email:
                return user
        return None

    def get_by_username(self, username: str) -> _FakeUser | None:
        for user in self._store["users"]:
            if user.username == username:
                return user
        return None

    def set_last_login(self, user_id: uuid.UUID, ts: datetime) -> None:
        for user in self._store["users"]:
            if user.id == user_id:
                user.last_login = ts
                return


class _FakeAuditRepo:
    def __init__(self, session) -> None:
        self._store = session

    def write(self, entry) -> None:
        self._store["audit_entries"].append(entry)


def test_default_admin_bootstrap_init_login_and_audit(monkeypatch) -> None:
    shared_store = {"users": [], "audit_entries": []}

    @contextmanager
    def _fake_session_scope():
        yield shared_store

    monkeypatch.setattr("quantsentinel.services.auth_service.session_scope", _fake_session_scope)
    monkeypatch.setattr("quantsentinel.services.auth_service.UsersRepo", _FakeUsersRepo)
    monkeypatch.setattr("quantsentinel.services.auth_service.AuditRepo", _FakeAuditRepo)

    service = AuthService()

    created = service.ensure_default_admin(
        username="admin",
        email="admin@example.com",
        password="Admin@123456",
        default_language="zh_CN",
    )

    login_result = service.login(identifier="admin", password="Admin@123456")

    assert created.username == "admin"
    assert created.default_language == "zh_CN"
    assert login_result.ok is True
    assert login_result.user_id == created.id
    assert login_result.default_language == "zh_CN"

    audit_actions = [entry.action for entry in shared_store["audit_entries"]]
    assert "bootstrap_admin_created" in audit_actions
    assert "login_success" in audit_actions
