from __future__ import annotations

from typing import TYPE_CHECKING

import streamlit as st

if TYPE_CHECKING:
    from collections.abc import Callable

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


def loading(message: str) -> None:
    with st.container(border=True):
        st.caption("⏳")
        st.write(message)


def empty(message: str) -> None:
    with st.container(border=True):
        st.caption("📭")
        st.write(message)


def success(message: str) -> None:
    with st.container(border=True):
        st.caption("✅")
        st.write(message)


def error(
    message: str,
    *,
    on_retry: Callable[[], None] | None = None,
    on_view_logs: Callable[[], None] | None = None,
    retry_label: str = "Retry",
    logs_label: str = "View Logs",
    key_prefix: str = "state_error",
) -> None:
    with st.container(border=True):
        st.caption("❌")
        st.write(message)
        retry_col, logs_col = st.columns(2)
        with retry_col:
            retry_clicked = st.button(retry_label, key=f"{key_prefix}_retry", use_container_width=True)
            if retry_clicked and on_retry is not None:
                on_retry()
        with logs_col:
            logs_clicked = st.button(logs_label, key=f"{key_prefix}_logs", use_container_width=True)
            if logs_clicked and on_view_logs is not None:
                on_view_logs()


# Backward-compatible aliases.
def render_loading_state(message: str) -> None:
    loading(message)


def render_empty_state(message: str) -> None:
    empty(message)


def render_success_state(message: str) -> None:
    success(message)


def render_error_state(
    message: str,
    *,
    on_retry: Callable[[], None] | None = None,
    on_view_logs: Callable[[], None] | None = None,
    retry_label: str = "Retry",
    logs_label: str = "View Logs",
    key_prefix: str = "state_error",
) -> None:
    error(
        message,
        on_retry=on_retry,
        on_view_logs=on_view_logs,
        retry_label=retry_label,
        logs_label=logs_label,
        key_prefix=key_prefix,
    )
