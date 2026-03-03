from __future__ import annotations

from pathlib import Path


WORKSPACE_PAGES = [
    "market.py",
    "explore.py",
    "monitor.py",
    "research_lab.py",
    "strategy_lab.py",
    "admin.py",
    "help.py",
]


def _read(path: str) -> str:
    return Path(path).read_text(encoding="utf-8")


def test_workspace_shell_template_snapshot() -> None:
    layout_text = _read("src/quantsentinel/app/ui/layout.py")
    assert 'data-testid="workspace-toolbar"' in layout_text
    assert 'data-testid="workspace-drawer"' in layout_text
    assert "def render_workspace_shell(" in layout_text


def test_each_workspace_has_toolbar_and_drawer_sections() -> None:
    for page in WORKSPACE_PAGES:
        content = _read(f"src/quantsentinel/app/pages/{page}")
        assert "render_workspace_shell(" in content, f"{page} must use shared shell"
        assert "_render_toolbar" in content, f"{page} must define toolbar section"
        assert "_render_drawer" in content, f"{page} must define drawer section"


def test_detail_drawer_does_not_use_sidebar() -> None:
    drawer_text = _read("src/quantsentinel/app/ui/drawer.py")
    assert "st.sidebar" not in drawer_text
