from quantsentinel.infra.db.models import UserRole
from quantsentinel.services.auth_service import AuthService
from quantsentinel.services.layout_service import LayoutService


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
