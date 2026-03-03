from __future__ import annotations

from typing import Callable
from quantsentinel.app.ui.state import ui

def register_shortcuts(shortcuts: dict[str, str]) -> None:
    """
    Retain a registry of shortcuts in UI state (no native support yet).
    (Third-party component support could be added later.)
    """
    u = ui()
    u.shortcuts_help_open = True  # we mark help open to display mapping