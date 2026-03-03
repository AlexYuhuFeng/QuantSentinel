from __future__ import annotations

from typing import Callable

import streamlit as st

from quantsentinel.app.ui.state import auth, ui
from quantsentinel.i18n.gettext import get_translator


def button(label: str, *, key: str | None = None, on_click: Callable | None = None) -> bool:
    return st.button(label, key=key, on_click=on_click)


def text_input(label: str, *, key: str | None = None, value: str = "") -> str:
    return st.text_input(label, key=key, value=value)


def render_shortcuts_help_dialog() -> None:
    current_ui = ui()
    if not current_ui.shortcuts_help_open:
        return

    t = get_translator(auth().language)
    shortcuts = current_ui.shortcuts_registry or {}

    @st.dialog(t("Keyboard shortcuts"))
    def _dialog() -> None:
        if shortcuts:
            st.table([{t("Shortcut"): key, t("Action"): action} for key, action in shortcuts.items()])
        else:
            st.caption(t("No shortcuts registered."))
        if st.button(t("Close"), key="qs_shortcuts_help_close"):
            close_ui = ui()
            close_ui.shortcuts_help_open = False
            st.session_state["qs_ui"] = close_ui
            st.rerun()

    _dialog()
