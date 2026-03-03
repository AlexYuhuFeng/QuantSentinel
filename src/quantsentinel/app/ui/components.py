from __future__ import annotations

import streamlit as st
from typing import Callable

from quantsentinel.app.ui.state import ui

def button(label: str, *, key: str | None = None, on_click: Callable | None = None) -> bool:
    return st.button(label, key=key, on_click=on_click)

def text_input(label: str, *, key: str | None = None, value: str = "") -> str:
    return st.text_input(label, key=key, value=value)


def render_shortcuts_help_dialog() -> None:
    u = ui()
    if not u.shortcuts_help_open:
        return

    shortcuts = u.shortcuts_registry or {}

    @st.dialog("Keyboard shortcuts")
    def _dialog() -> None:
        if shortcuts:
            st.table(
                [
                    {"Shortcut": key, "Action": action}
                    for key, action in shortcuts.items()
                ]
            )
        else:
            st.caption("No shortcuts registered.")
        if st.button("Close", key="qs_shortcuts_help_close"):
            close_u = ui()
            close_u.shortcuts_help_open = False
            st.session_state["qs_ui"] = close_u
            st.rerun()

    _dialog()
