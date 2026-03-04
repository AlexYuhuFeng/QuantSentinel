from __future__ import annotations

import streamlit as st

from quantsentinel.app.ui.components import success
from quantsentinel.app.ui.drawer import Drawer
from quantsentinel.app.ui.layout import render_workspace_shell
from quantsentinel.app.ui.state import auth, open_drawer
from quantsentinel.i18n.gettext import get_translator


def render() -> None:
    t = get_translator(auth().language)

    def _render_toolbar() -> None:
        st.markdown(f"## {t('Help & Documentation')}")
        st.caption(t("Workspace guides and FAQs"))

    def _render_main() -> None:
        if st.button(t("Details"), key="help_details"):
            open_drawer("help", {"topic": "workspace_guides"})
            st.rerun()
        st.header(t("Getting Started"))
        st.markdown(
            f"""
- ⭐ **{t('Explore')}** — {t('Visualize price data and derived indicators for any ticker.')}
- 🧠 **{t('Monitor')}** — {t('View and manage rules to detect market conditions automatically.')}
- 📊 **{t('Research')}** — {t('Run backtests and analyze strategies against historical data.')}
- 🛠️ **{t('Strategy')}** — {t('Develop and test trading strategies within the integrated environment.')}
- 👤 **{t('Admin')}** — {t('Manage users, view audit logs, and configure your workspace.')}
"""
        )
        st.header(t("Tips & Tricks"))
        st.markdown(
            f"""
- {t('Use the search box to quickly find instruments or indicators.')}
- {t('Click on charts to explore data interactively.')}
- {t('Remember to refresh data before running research or alerts.')}
"""
        )
        success(t("Help center loaded"))

    def _render_drawer() -> None:
        Drawer.render(title=t("Details"))

    render_workspace_shell(render_toolbar=_render_toolbar, render_main=_render_main, render_drawer=_render_drawer)
