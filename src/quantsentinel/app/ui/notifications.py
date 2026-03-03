from __future__ import annotations

from typing import Callable

import streamlit as st

from quantsentinel.app.ui.state import ui


def render_notifications_control(t: Callable[[str], str]) -> None:
    state = ui()
    notifications = state.notifications or []
    unread_count = sum(1 for item in notifications if item.get("unread", False))

    with st.popover(f"🔔 {t('Notifications')} ({unread_count})", use_container_width=False):
        st.caption(t("Recent notifications"))

        if not notifications:
            st.info(t("No notifications"))
            return

        for item in notifications[:5]:
            title = item.get("title", t("Notification"))
            message = item.get("message", "")
            prefix = "• " if item.get("unread", False) else ""
            st.write(f"{prefix}**{title}**")
            if message:
                st.caption(message)
            st.divider()
