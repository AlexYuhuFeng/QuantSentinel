from quantsentinel.infra.db.models import UserRole
from quantsentinel.services.auth_service import AuthService
from quantsentinel.services.layout_service import LayoutService
from quantsentinel.services.rbac_service import AuditActionType, RBACService


def test_auth_rbac_gating_matrix() -> None:
    assert AuthService.can_manage_users(UserRole.ADMIN) is True
    assert AuthService.can_manage_users(UserRole.EDITOR) is False
    assert AuthService.can_edit(UserRole.ADMIN) is True
    assert AuthService.can_edit(UserRole.EDITOR) is True
    assert AuthService.can_edit(UserRole.VIEWER) is False
    assert AuthService.can_view(UserRole.VIEWER) is True


def test_layout_manage_rbac_gating() -> None:
    assert LayoutService.can_manage_layouts(UserRole.ADMIN) is True
    assert LayoutService.can_manage_layouts(UserRole.EDITOR) is True
    assert LayoutService.can_manage_layouts(UserRole.VIEWER) is False


def test_workspace_role_matrix_for_navigation_buttons() -> None:
    workspaces = ("Market", "Explore", "Monitor", "Research", "Strategy", "Admin")

    assert RBACService.can_view_workspace(UserRole.ADMIN, "Admin") is True
    assert RBACService.can_view_workspace(UserRole.EDITOR, "Admin") is False
    assert RBACService.can_view_workspace(UserRole.VIEWER, "Admin") is False

    for workspace in workspaces:
        if workspace == "Admin":
            continue
        assert RBACService.can_view_workspace(UserRole.VIEWER, workspace) is True
        assert RBACService.can_mutate_workspace(UserRole.VIEWER, workspace) is False
        assert RBACService.can_mutate_workspace(UserRole.EDITOR, workspace) is True
        assert RBACService.can_mutate_workspace(UserRole.ADMIN, workspace) is True


def test_service_side_permission_denied_for_viewer_mutation() -> None:
    try:
        RBACService.ensure_workspace_mutation_allowed(
            role=UserRole.VIEWER,
            workspace="Monitor",
            action=AuditActionType.CREATE,
        )
    except PermissionError:
        pass
    else:
        raise AssertionError("Viewer should not mutate monitor workspace.")
