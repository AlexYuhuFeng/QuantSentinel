from __future__ import annotations

import streamlit as st
from typing import Callable

from quantsentinel.app.ui.state import ui, open_drawer, close_drawer

class CommandPalette:
    """
    A simple command palette UI that filters registered commands.
    """

    def __init__(self) -> None:
        self._commands: dict[str, tuple[str, Callable]] = {}

    def register(self, key: str, label: str, action: Callable) -> None:
        """
        Register a command key, label, and the function to call.
        """
        self._commands[key] = (label, action)

    def show(self) -> None:
        """
        Renders the palette and executes selected action.
        """
        u = ui()
        query = st.text_input("Command palette...", value=u.command_palette_query)
        u.command_palette_query = query
        if query:
            matches = {
                k: v
                for k, v in self._commands.items()
                if query.lower() in v[0].lower()
            }
            for key, (label, action) in matches.items():
                if st.button(label):
                    action()
                    u.command_palette_open = False
                    st.experimental_rerun()