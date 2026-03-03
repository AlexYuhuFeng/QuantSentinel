from __future__ import annotations
import streamlit as st
from typing import Callable

from quantsentinel.app.ui.state import ui, close_drawer

class Drawer:
    """
    Sidebar drawer driven by UI state.
    """

    @staticmethod
    def render(render_fn: Callable[[dict[str, object]], None]) -> None:
        """
        Renders the drawer if open, dispatching based on kind/payload.
        """
        u = ui()
        if not u.drawer_open:
            return

        with st.sidebar:
            st.markdown(f"## {u.drawer_kind}")
            render_fn(u.drawer_payload)
            if st.button("Close"):
                close_drawer()
                st.experimental_rerun()