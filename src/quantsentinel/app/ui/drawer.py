from __future__ import annotations

from typing import TYPE_CHECKING

import streamlit as st

from quantsentinel.app.ui.state import auth, close_drawer, ui
from quantsentinel.i18n.gettext import get_translator

if TYPE_CHECKING:
    from collections.abc import Callable


class Drawer:
    """Right-side details drawer driven by UI state."""

    @staticmethod
    def render(
        *,
        render_fn: Callable[[dict[str, object] | None], None] | None = None,
        title: str | None = None,
    ) -> None:
        u = ui()
        t = get_translator(auth().language)
        if not u.drawer_open:
            st.caption(t("No selection"))
            return

        st.markdown(f"## {title or t('Details')}")
        if u.drawer_kind:
            st.caption(u.drawer_kind)

        if render_fn is not None:
            render_fn(u.drawer_payload)
        elif u.drawer_payload:
            st.json(u.drawer_payload)

        if st.button(t("Close")):
            close_drawer()
            st.rerun()
