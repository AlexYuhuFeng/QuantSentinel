from __future__ import annotations

import streamlit as st
from typing import Callable

def button(label: str, *, key: str | None = None, on_click: Callable | None = None) -> bool:
    return st.button(label, key=key, on_click=on_click)

def text_input(label: str, *, key: str | None = None, value: str = "") -> str:
    return st.text_input(label, key=key, value=value)