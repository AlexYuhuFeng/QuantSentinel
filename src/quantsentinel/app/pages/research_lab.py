from __future__ import annotations

from datetime import date

import streamlit as st

from quantsentinel.app.ui.state import auth, app_state, push_toast
from quantsentinel.i18n.gettext import get_translator
from quantsentinel.services.research_service import ResearchService
from quantsentinel.services.task_service import TaskService


def render() -> None:
    """
    Research Lab page.

    Provides ability to configure and run research/backtests
    with interactive parameter inputs and output displays.
    """
    a = auth()
    t = get_translator(a.language)

    st.markdown(f"## {t('Research Lab')}")

    svc_research = ResearchService()
    svc_task = TaskService()

    # --- Ticker & Date Inputs ---

    col1, col2 = st.columns(2)
    with col1:
        ticker = st.text_input(
            t("Enter ticker for research"),
            value=app_state.get("research_ticker", ""),
        ).upper().strip()
        app_state["research_ticker"] = ticker

    with col2:
        date_range = st.date_input(
            t("Date range"),
            value=(
                app_state.get("research_start", date.today().replace(year=date.today().year - 1)),
                app_state.get("research_end", date.today()),
            ),
        )
        if len(date_range) == 2:
            start_date, end_date = date_range
            app_state["research_start"], app_state["research_end"] = start_date, end_date
        else:
            start_date = end_date = None

    if ticker and (start_date is None or end_date is None or start_date > end_date):
        st.error(t("Invalid date range"))
        return

    st.divider()

    # --- Algorithm/Strategy Selection ---

    st.subheader(t("Research Configuration"))

    family = st.selectbox(
        t("Select strategy family"),
        options=svc_research.available_families(),
        index=0,
    )

    params = svc_research.default_params(family)
    param_inputs = {}
    for p_name, p_default in params.items():
        param_inputs[p_name] = st.text_input(f"{p_name}", value=str(p_default))

    # --- Run Backtest / Research ---

    st.subheader(t("Backtest Controls"))

    if st.button(t("Run Backtest")):
        if not ticker:
            st.warning(t("Please enter a ticker"))
        else:
            with st.spinner(t("Starting research...")):
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

    st.divider()

    # --- Show Recent Results / Status ---

    st.subheader(t("Recent Research Results"))

    results = svc_research.get_recent_results(limit=10)
    if not results:
        st.info(t("No research results available"))
        return

    for r in results:
        _show_result_card(r, t)