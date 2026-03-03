from __future__ import annotations

from typing import Callable

from quantsentinel.app.ui.state import auth, close_drawer, ui
from quantsentinel.i18n.gettext import get_translator

class Drawer:
    """Right-side details drawer driven by UI state."""

    @staticmethod
    def render(
        *,
        render_fn: Callable[[str | None, dict[str, object]], None] | None = None,
        title: str = "Details",
    ) -> None:
        u = ui()
        t = get_translator(auth().language)
        if not u.drawer_open:
            st.caption("No selection")
            return

        with st.sidebar:
            st.markdown(f"## {u.drawer_kind}")
            render_fn(u.drawer_payload)
            if st.button(t("Close")):
                close_drawer()
                st.experimental_rerun()
