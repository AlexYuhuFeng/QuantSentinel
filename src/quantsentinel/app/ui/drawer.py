from __future__ import annotations

from typing import Callable

import streamlit as st

from quantsentinel.app.ui.state import close_drawer, ui


class Drawer:
    """Right-side details drawer driven by UI state."""

    @staticmethod
    def render(
        *,
        render_fn: Callable[[str | None, dict[str, object]], None] | None = None,
        title: str = "Details",
    ) -> None:
        u = ui()

        st.markdown(f"### {title}")
        if not u.drawer_open:
            st.caption("No selection")
            return

        payload: dict[str, object] = (u.drawer_payload or {})
        st.caption(f"Kind: {u.drawer_kind or '-'}")

        if render_fn is None:
            st.json(payload)
        else:
            render_fn(u.drawer_kind, payload)

        if st.button("Close", key="drawer_close"):
            close_drawer()
            st.rerun()
