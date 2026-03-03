from __future__ import annotations

from dataclasses import dataclass
from difflib import SequenceMatcher
from typing import Any, Callable

import streamlit as st

from quantsentinel.app.ui.state import auth, ui
from quantsentinel.i18n.gettext import get_translator

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
        t = get_translator(auth().language)
        u = ui()
        query = st.text_input(t("Command palette..."), value=u.command_palette_query)
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
