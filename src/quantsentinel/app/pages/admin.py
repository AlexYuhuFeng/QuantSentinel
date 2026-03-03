from __future__ import annotations

import streamlit as st

from quantsentinel.app.ui.drawer import Drawer
from quantsentinel.app.ui.layout import render_workspace_shell
from quantsentinel.app.ui.state import auth
from quantsentinel.i18n.gettext import get_translator
from quantsentinel.infra.db.models import UserRole


def render() -> None:
    a = auth()
    t = get_translator(a.language)

    if a.role != UserRole.ADMIN:
        st.error(t("Access denied — admin only."))
        return

    state = {"section": t("Users")}

    def _render_toolbar() -> None:
        st.markdown(f"## {t('Admin Console')}")
        state["section"] = st.radio(label=t("Select section"), options=[t("Users"), t("Audit Logs")], horizontal=True)

    def _render_main() -> None:
        if state["section"] == t("Users"):
            st.subheader(t("Manage Users"))
            st.info(t("User management is available in service-backed deployments."))
        else:
            st.subheader(t("Audit Logs"))
            st.info(t("Audit logs are available in service-backed deployments."))

    def _render_drawer() -> None:
        Drawer.render(title=t("Details"))

    render_workspace_shell(render_toolbar=_render_toolbar, render_main=_render_main, render_drawer=_render_drawer)
