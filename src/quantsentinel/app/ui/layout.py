from __future__ import annotations
import streamlit as st
from contextlib import contextmanager

@contextmanager
def page_section(title: str) -> None:
    st.markdown(f"### {title}")
    yield
    st.divider()