"""
Authentication & user management service.

Responsibilities:
- Login (verify password)
- Create default admin (bootstrap)
- Change password
- Update language preference
- RBAC helpers
- Write audit log for security-sensitive operations

Non-responsibilities:
- UI/session state (handled by app layer)
- Token issuance (Team Edition v1 uses Streamlit session cookie only)
"""

from __future__ import annotations

import uuid
from dataclasses import dataclass
from datetime import datetime, timezone

from quantsentinel.common.security import hash_password, verify_password
from quantsentinel.infra.db.engine import session_scope
from quantsentinel.infra.db.models import User, UserRole
from quantsentinel.infra.db.repos.audit_repo import AuditEntryCreate, AuditRepo
from quantsentinel.infra.db.repos.users_repo import UserCreate, UsersRepo


@dataclass(frozen=True)
class LoginResult:
    ok: bool
    user_id: uuid.UUID | None
    username: str | None
    role: UserRole | None
    default_language: str | None
    error: str | None = None


class AuthService:
    """
    Service for authentication and user profile operations.
    """

    # -----------------------------
    # Bootstrap
    # -----------------------------

    def ensure_default_admin(
        self,
        *,
        username: str,
        email: str,
        password: str,
        default_language: str = "en",
    ) -> User:
        """
        Create a default Admin user ONLY if there are no users in the system.
        Idempotent: if any user exists, returns the existing Admin if present,
        otherwise raises.

        This is intended for initial bootstrap in a fresh DB.
        """
        now = datetime.now(timezone.utc)

        with session_scope() as session:
            users = UsersRepo(session)
            audit = AuditRepo(session)

            if users.count_users() > 0:
                existing_admin = users.ensure_admin_exists()
                if existing_admin is not None:
                    return existing_admin
                raise RuntimeError("Users already exist but no Admin found; bootstrap aborted.")

            admin = users.create(
                UserCreate(
                    username=username,
                    email=email,
                    password_hash=hash_password(password),
                    role=UserRole.ADMIN,
                    default_language=default_language,
                    is_active=True,
                )
            )

            audit.write(
                AuditEntryCreate(
                    action="bootstrap_admin_created",
                    entity_type="user",
                    entity_id=str(admin.id),
                    actor_id=None,
                    payload={"username": username, "email": email, "role": admin.role.value, "ts": now.isoformat()},
                    ts=now,
                )
            )
            return admin

    # -----------------------------
    # Login
    # -----------------------------

    def login(self, identifier: str, password: str) -> LoginResult:
        """
        Login using username OR email.

        Args:
            identifier: username or email
            password: plaintext password

        Returns:
            LoginResult
        """
        now = datetime.now(timezone.utc)

        with session_scope() as session:
            users = UsersRepo(session)
            audit = AuditRepo(session)

            # determine lookup
            user: User | None
            if "@" in identifier:
                user = users.get_by_email(identifier.strip().lower())
            else:
                user = users.get_by_username(identifier.strip())

            if user is None:
                audit.write(
                    AuditEntryCreate(
                        action="login_failed",
                        entity_type="auth",
                        entity_id=None,
                        actor_id=None,
                        payload={"reason": "user_not_found", "identifier": identifier},
                        ts=now,
                    )
                )
                return LoginResult(
                    ok=False,
                    user_id=None,
                    username=None,
                    role=None,
                    default_language=None,
                    error="Invalid credentials.",
                )

            if not user.is_active:
                audit.write(
                    AuditEntryCreate(
                        action="login_failed",
                        entity_type="auth",
                        entity_id=str(user.id),
                        actor_id=user.id,
                        payload={"reason": "inactive_user"},
                        ts=now,
                    )
                )
                return LoginResult(
                    ok=False,
                    user_id=None,
                    username=None,
                    role=None,
                    default_language=None,
                    error="User is inactive.",
                )

            if not verify_password(user.password_hash, password):
                audit.write(
                    AuditEntryCreate(
                        action="login_failed",
                        entity_type="auth",
                        entity_id=str(user.id),
                        actor_id=user.id,
                        payload={"reason": "bad_password"},
                        ts=now,
                    )
                )
                return LoginResult(
                    ok=False,
                    user_id=None,
                    username=None,
                    role=None,
                    default_language=None,
                    error="Invalid credentials.",
                )

            users.set_last_login(user.id, now)

            audit.write(
                AuditEntryCreate(
                    action="login_success",
                    entity_type="auth",
                    entity_id=str(user.id),
                    actor_id=user.id,
                    payload={"username": user.username, "role": user.role.value},
                    ts=now,
                )
            )

            return LoginResult(
                ok=True,
                user_id=user.id,
                username=user.username,
                role=user.role,
                default_language=user.default_language,
                error=None,
            )

    # -----------------------------
    # User profile operations
    # -----------------------------

    def change_password(self, actor_id: uuid.UUID, user_id: uuid.UUID, new_password: str) -> None:
        """
        Change password for a user.
        Actor may be the same user, or an Admin.

        RBAC should be enforced by caller (UI/service orchestration).
        """
        now = datetime.now(timezone.utc)

        with session_scope() as session:
            users = UsersRepo(session)
            audit = AuditRepo(session)

            target = users.get(user_id)
            if target is None:
                raise ValueError("User not found.")

            users.set_password_hash(user_id, hash_password(new_password))

            audit.write(
                AuditEntryCreate(
                    action="password_changed",
                    entity_type="user",
                    entity_id=str(user_id),
                    actor_id=actor_id,
                    payload={"target_user_id": str(user_id)},
                    ts=now,
                )
            )

    def set_default_language(self, actor_id: uuid.UUID, user_id: uuid.UUID, language: str) -> None:
        """
        Update user's default language preference.
        """
        now = datetime.now(timezone.utc)

        with session_scope() as session:
            users = UsersRepo(session)
            audit = AuditRepo(session)

            if users.get(user_id) is None:
                raise ValueError("User not found.")

            users.set_default_language(user_id, language)

            audit.write(
                AuditEntryCreate(
                    action="user_language_updated",
                    entity_type="user",
                    entity_id=str(user_id),
                    actor_id=actor_id,
                    payload={"language": language},
                    ts=now,
                )
            )

    # -----------------------------
    # RBAC helpers
    # -----------------------------

    @staticmethod
    def can_manage_users(role: UserRole) -> bool:
        return role == UserRole.ADMIN

    @staticmethod
    def can_edit(role: UserRole) -> bool:
        return role in (UserRole.ADMIN, UserRole.EDITOR)

    @staticmethod
    def can_view(role: UserRole) -> bool:
        return True