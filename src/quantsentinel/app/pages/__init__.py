"""
Expose application page render functions.

This module re-exports all page render entrypoints in a flat namespace,
so other parts of the application (e.g., app/main.py) can import
them without needing to know the individual module names.

Each page module must implement a callable `render()` function.
"""

from __future__ import annotations

from typing import TYPE_CHECKING

from .admin import render as admin
from .explore import render as explore
from .help import render as help
from .market import render as market
from .monitor import render as monitor
from .research_lab import render as research_lab
from .strategy_lab import render as strategy_lab

if TYPE_CHECKING:
    from collections.abc import Callable

# Mapping workspace identifier → render callable
# This can be useful if you want to dispatch dynamically:
pages: dict[str, Callable[[], None]] = {
    "Admin": admin,
    "Explore": explore,
    "Help": help,
    "Market": market,
    "Monitor": monitor,
    "Research": research_lab,
    "Strategy": strategy_lab,
}