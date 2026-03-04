from __future__ import annotations

from datetime import date
from typing import Any

import pandas as pd
import streamlit as st

from quantsentinel.app.ui.components import (
    render_empty_state,
    render_error_state,
    render_success_state,
)
from quantsentinel.app.ui.drawer import Drawer
from quantsentinel.app.ui.layout import render_workspace_shell
from quantsentinel.app.ui.state import app_state, auth
from quantsentinel.i18n.gettext import get_translator
from quantsentinel.services.strategy_service import StrategyService
from quantsentinel.services.task_service import TaskService
from quantsentinel.services.rbac_service import RBACService


def render() -> None:
    t = get_translator(auth().language)
    state = app_state()
    svc_strategy = StrategyService()
    svc_task = TaskService()
    can_mutate = auth().role is not None and RBACService.can_mutate_workspace(auth().role, "Strategy")

    def _render_toolbar() -> None:
        st.markdown(f"## {t('Strategy Lab')}")
        c1, c2, c3 = st.columns([2, 1, 1])
        with c1:
            state["strategy_ticker"] = st.text_input(t("Ticker (for strategy)"), value=state.get("strategy_ticker", "")).strip().upper()
        with c2:
            state["strategy_start"] = st.date_input(t("Start Date"), value=state.get("strategy_start", date.today().replace(year=date.today().year - 2)))
        with c3:
            state["strategy_end"] = st.date_input(t("End Date"), value=state.get("strategy_end", date.today()))

    def _render_main() -> None:
        if state["strategy_start"] > state["strategy_end"]:
            render_error_state(
                t("Start date must be before end date"),
                retry_label=t("Retry"),
                logs_label=t("View Logs"),
                key_prefix="strategy_date_error",
            )
            return
        families = svc_strategy.available_families()
        family = st.selectbox(t("Strategy Family"), families)
        defaults = svc_strategy.default_params(family=family)
        params: dict[str, Any] = {k: st.text_input(k, value=str(v)) for k, v in defaults.items()}

        run, sweep = st.columns(2)
        with run:
            if can_mutate and st.button(t("Run Backtest")):
                _run_backtest(t, svc_task, state["strategy_ticker"], state["strategy_start"], state["strategy_end"], family, params)
        with sweep:
            if can_mutate and st.button(t("Parameter Sweep")):
                _run_parameter_sweep(t, svc_task, state["strategy_ticker"], state["strategy_start"], state["strategy_end"], family, defaults)

        if not can_mutate:
            st.caption(t("Viewer mode: read-only."))
        st.header(t("Recent Strategy Results"))
        results = svc_strategy.get_recent_results(limit=20)
        if not results:
            render_empty_state(t("No strategy results available"))
            return
        for r in results:
            st.markdown(f"### {r.family} — {r.ticker}")
            st.dataframe(pd.DataFrame(r.metrics_json))

    def _render_drawer() -> None:
        Drawer.render(title=t("Details"))

    render_workspace_shell(render_toolbar=_render_toolbar, render_main=_render_main, render_drawer=_render_drawer)


def _run_backtest(t, svc_task: TaskService, ticker: str, start: date, end: date, family: str, params: dict[str, Any]) -> None:
    if not ticker:
        render_empty_state(t("Please enter a ticker"))
        return
    try:
        svc_task.create_task(
            task_type="strategy_backtest",
            celery_signature=None,
            celery_args={
                "ticker": ticker,
                "start_date": start.isoformat(),
                "end_date": end.isoformat(),
                "family": family,
                "params_json": params,
            },
        )
        render_success_state(t("Backtest queued"))
    except Exception as e:
        render_error_state(
            f"{t('Failed to queue backtest')}: {e}",
            retry_label=t("Retry"),
            logs_label=t("View Logs"),
            key_prefix="strategy_backtest_error",
        )


def _run_parameter_sweep(t, svc_task: TaskService, ticker: str, start: date, end: date, family: str, base_params: dict[str, Any]) -> None:
    try:
        for combo in svc_task.parameter_grid_combinations(base_params):
            svc_task.create_task(
                task_type="strategy_backtest",
                celery_signature=None,
                celery_args={
                    "ticker": ticker,
                    "start_date": start.isoformat(),
                    "end_date": end.isoformat(),
                    "family": family,
                    "params_json": combo,
                },
            )
        render_success_state(t("Parameter sweep queued"))
    except Exception as e:
        render_error_state(
            f"{t('Failed to queue parameter sweep')}: {e}",
            retry_label=t("Retry"),
            logs_label=t("View Logs"),
            key_prefix="strategy_sweep_error",
        )
