from __future__ import annotations
import streamlit as st
from quantsentinel.app.ui.state import ui, _ensure_defaults

def flush_toasts() -> None:
    """
    Drain UI toast queue and display toasts.
    Should be called at top of each page.
    """
    _ensure_defaults()
    u = ui()
    if not u.toast_queue:
        return

    for msg in list(u.toast_queue):
        kind = msg.get("kind", "info")
        text = msg.get("message", "")
        # Map kind to icon emoji
        icon = {
            "info": "ℹ️",
            "success": "✅",
            "warning": "⚠️",
            "error": "❌",
        }.get(kind, None)
        st.toast(text, icon=icon)
    u.toast_queue.clear()
    st.session_state["qs_ui"] = u