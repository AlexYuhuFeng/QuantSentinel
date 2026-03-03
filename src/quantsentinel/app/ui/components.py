from __future__ import annotations

from typing import Callable

import streamlit as st


def button(label: str, *, key: str | None = None, on_click: Callable | None = None) -> bool:
    return st.button(label, key=key, on_click=on_click)


def text_input(label: str, *, key: str | None = None, value: str = "") -> str:
    return st.text_input(label, key=key, value=value)


def show_loading(message: str = "Loading...") -> None:
    st.info(f"⏳ {message}")


def show_empty(message: str = "No data.") -> None:
    st.info(message)


def show_success(message: str) -> None:
    st.success(message)


def show_error(
    message: str,
    *,
    on_retry: Callable[[], None] | None = None,
    on_view_logs: Callable[[], None] | None = None,
    retry_label: str = "Retry",
    logs_label: str = "View Logs",
) -> None:
    st.error(message)
    retry_col, logs_col = st.columns(2)
    with retry_col:
        if st.button(retry_label, key=f"{retry_label}_action") and on_retry:
            on_retry()
    with logs_col:
        if st.button(logs_label, key=f"{logs_label}_action") and on_view_logs:
            on_view_logs()
