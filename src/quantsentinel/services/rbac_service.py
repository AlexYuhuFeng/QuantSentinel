from __future__ import annotations

from dataclasses import dataclass
from enum import Enum

from quantsentinel.infra.db.models import UserRole


class AuditActionType(str, Enum):
    CREATE = "create"
    UPDATE = "update"
    DELETE = "delete"
    RUN = "run"
    ACK = "ack"
    EXPORT = "export"


@dataclass(frozen=True)
class WorkspaceAccess:
    can_view: bool
    can_mutate: bool


_WORKSPACE_ACCESS: dict[str, dict[UserRole, WorkspaceAccess]] = {
    "Market": {
        UserRole.ADMIN: WorkspaceAccess(can_view=True, can_mutate=True),
        UserRole.EDITOR: WorkspaceAccess(can_view=True, can_mutate=True),
        UserRole.VIEWER: WorkspaceAccess(can_view=True, can_mutate=False),
    },
    "Explore": {
        UserRole.ADMIN: WorkspaceAccess(can_view=True, can_mutate=True),
        UserRole.EDITOR: WorkspaceAccess(can_view=True, can_mutate=True),
        UserRole.VIEWER: WorkspaceAccess(can_view=True, can_mutate=False),
    },
    "Monitor": {
        UserRole.ADMIN: WorkspaceAccess(can_view=True, can_mutate=True),
        UserRole.EDITOR: WorkspaceAccess(can_view=True, can_mutate=True),
        UserRole.VIEWER: WorkspaceAccess(can_view=True, can_mutate=False),
    },
    "Research": {
        UserRole.ADMIN: WorkspaceAccess(can_view=True, can_mutate=True),
        UserRole.EDITOR: WorkspaceAccess(can_view=True, can_mutate=True),
        UserRole.VIEWER: WorkspaceAccess(can_view=True, can_mutate=False),
    },
    "Strategy": {
        UserRole.ADMIN: WorkspaceAccess(can_view=True, can_mutate=True),
        UserRole.EDITOR: WorkspaceAccess(can_view=True, can_mutate=True),
        UserRole.VIEWER: WorkspaceAccess(can_view=True, can_mutate=False),
    },
    "Admin": {
        UserRole.ADMIN: WorkspaceAccess(can_view=True, can_mutate=True),
        UserRole.EDITOR: WorkspaceAccess(can_view=False, can_mutate=False),
        UserRole.VIEWER: WorkspaceAccess(can_view=False, can_mutate=False),
    },
}


class RBACService:
    @staticmethod
    def workspace_access(role: UserRole, workspace: str) -> WorkspaceAccess:
        return _WORKSPACE_ACCESS.get(workspace, {}).get(role, WorkspaceAccess(can_view=False, can_mutate=False))

    @staticmethod
    def can_view_workspace(role: UserRole, workspace: str) -> bool:
        return RBACService.workspace_access(role, workspace).can_view

    @staticmethod
    def can_mutate_workspace(role: UserRole, workspace: str) -> bool:
        return RBACService.workspace_access(role, workspace).can_mutate

    @staticmethod
    def can_manage_users(role: UserRole) -> bool:
        return role == UserRole.ADMIN

    @staticmethod
    def ensure_workspace_mutation_allowed(*, role: UserRole | None, workspace: str, action: AuditActionType) -> None:
        if role is None or not RBACService.can_mutate_workspace(role, workspace):
            raise PermissionError(f"Permission denied for action '{action.value}' in workspace '{workspace}'.")

    @staticmethod
    def ensure_user_management_allowed(*, role: UserRole | None) -> None:
        if role is None or not RBACService.can_manage_users(role):
            raise PermissionError("Permission denied for user management.")
