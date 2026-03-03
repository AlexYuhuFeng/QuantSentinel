from __future__ import annotations

from datetime import date

import streamlit as st

from quantsentinel.app.ui.drawer import Drawer
from quantsentinel.app.ui.layout import render_workspace_shell
from quantsentinel.app.ui.state import app_state, auth, push_toast
from quantsentinel.i18n.gettext import get_translator
from quantsentinel.services.research_service import ResearchService
from quantsentinel.services.task_service import TaskService


def render() -> None:
    t = get_translator(auth().language)
    state = app_state()
    svc_research = ResearchService()
    svc_task = TaskService()

    def _render_toolbar() -> None:
        st.markdown(f"## {t('Research Lab')}")
        c1, c2 = st.columns(2)
        with c1:
            state["research_ticker"] = st.text_input(
                t("Enter ticker for research"), value=state.get("research_ticker", "")
            ).upper().strip()
        with c2:
            st.caption(t("Date range"))
            state["research_start"] = st.date_input(
                t("Start"), value=state.get("research_start", date.today().replace(year=date.today().year - 1))
            )
            state["research_end"] = st.date_input(t("End"), value=state.get("research_end", date.today()))

    def _render_main() -> None:
        ticker = state.get("research_ticker", "")
        start_date = state.get("research_start")
        end_date = state.get("research_end")
        if ticker and (start_date is None or end_date is None or start_date > end_date):
            st.error(t("Invalid date range"))
            return

        st.subheader(t("Research Configuration"))
        family = st.selectbox(t("Select strategy family"), options=svc_research.available_families(), index=0)
        params = svc_research.default_params(family)
        param_inputs = {p_name: st.text_input(p_name, value=str(p_default)) for p_name, p_default in params.items()}

        if st.button(t("Run Backtest")):
            if not ticker:
                st.warning(t("Please enter a ticker"))
            else:
                try:
                    task_id = svc_task.create_task(task_type="research_backtest")
                    svc_task.start_task(
                        task_id,
                        task_args={
                            "ticker": ticker,
                            "start_date": start_date.isoformat(),
                            "end_date": end_date.isoformat(),
                            "family": family,
                            "params": param_inputs,
                        },
                    )
                    push_toast("success", t("Backtest queued"))
                except Exception as e:
                    push_toast("error", f"{t('Failed to start backtest')}: {e}")

        st.subheader(t("Recent Research Results"))
        results = svc_research.get_recent_results(limit=10)
        if not results:
            st.info(t("No research results available"))
            return
        for result in results:
            st.write(result)

    def _render_drawer() -> None:
        Drawer.render(title=t("Details"))

    render_workspace_shell(render_toolbar=_render_toolbar, render_main=_render_main, render_drawer=_render_drawer)
