from __future__ import annotations

import uuid
from typing import Any

import pandas as pd
import streamlit as st
from datetime import date

from quantsentinel.app.ui.state import auth, app_state, push_toast
from quantsentinel.i18n.gettext import get_translator
from quantsentinel.services.strategy_service import StrategyService
from quantsentinel.services.task_service import TaskService

# --------------------------------------------------------------------------
# STRATEGY LAB PAGE — BUILD, RUN, AND REVIEW STRATEGIES
# --------------------------------------------------------------------------

def render() -> None:
    """
    Strategy Lab — build strategies, run backtests, explore results.
    """
    a = auth()
    t = get_translator(a.language)

    st.markdown(f"## {t('Strategy Lab')}")

    svc_strategy = StrategyService()
    svc_task = TaskService()

    # ----------------------------------------------------------------------
    # STRATEGY BUILDER
    # ----------------------------------------------------------------------

    st.header(t("Strategy Builder"))

    ticker = st.text_input(
        t("Ticker (for strategy)"),
        value=app_state.get("strategy_ticker", ""),
    ).strip().upper()
    app_state["strategy_ticker"] = ticker

    col1, col2 = st.columns(2)
    with col1:
        start = st.date_input(
            t("Start Date"),
            value=app_state.get("strategy_start", date.today().replace(year=date.today().year - 2)),
        )
        app_state["strategy_start"] = start
    with col2:
        end = st.date_input(
            t("End Date"),
            value=app_state.get("strategy_end", date.today()),
        )
        app_state["strategy_end"] = end

    if start > end:
        st.error(t("Start date must be before end date"))
        return

    families = svc_strategy.available_families()
    family = st.selectbox(t("Strategy Family"), families)

    default_params = svc_strategy.default_params(family)

    st.subheader(t("Configure Parameters"))
    param_inputs: dict[str, Any] = {}
    for p_name, p_default in default_params.items():
        param_inputs[p_name] = st.text_input(f"{p_name}", value=str(p_default))

    col_run, col_sweep = st.columns([1, 1])
    with col_run:
        if st.button(t("Run Backtest")):
            _run_backtest(
                t=t,
                svc_task=svc_task,
                ticker=ticker,
                start=start,
                end=end,
                family=family,
                params=param_inputs,
            )

    with col_sweep:
        if st.button(t("Parameter Sweep")):
            _run_parameter_sweep(
                t=t,
                svc_task=svc_task,
                ticker=ticker,
                start=start,
                end=end,
                family=family,
                base_params=default_params,
            )

    st.divider()

    # ----------------------------------------------------------------------
    # RETURNING / LIST OF RESULTS
    # ----------------------------------------------------------------------

    st.header(t("Recent Strategy Results"))

    results = svc_strategy.get_recent_results(limit=20)

    if not results:
        st.info(t("No strategy results available"))
        return

    for r in results:
        _show_strategy_card(r, t)


# --------------------------------------------------------------------------
# BACKEND ACTIONS (QUEUE TASKS)
# --------------------------------------------------------------------------

def _run_backtest(
    *,
    t,
    svc_task: TaskService,
    ticker: str,
    start: date,
    end: date,
    family: str,
    params: dict[str, Any],
) -> None:
    if not ticker:
        st.warning(t("Please enter a ticker"))
        return

    try:
        payload = {
            "ticker": ticker,
            "start_date": start.isoformat(),
            "end_date": end.isoformat(),
            "family": family,
            "params_json": params,
        }
        task_id = svc_task.create_task(task_type="strategy_backtest", celery_signature=None, celery_args=payload)
        push_toast("success", t("Backtest queued"))
    except Exception as e:
        push_toast("error", f"{t('Failed to queue backtest')}: {e}")


def _run_parameter_sweep(
    *,
    t,
    svc_task: TaskService,
    ticker: str,
    start: date,
    end: date,
    family: str,
    base_params: dict[str, Any],
) -> None:
    """
    Trigger a parameter grid sweep (batch backtests).
    This could produce multiple tasks for each param combination.
    """
    try:
        for combo in svc_task.parameter_grid_combinations(base_params):
            payload = {
                "ticker": ticker,
                "start_date": start.isoformat(),
                "end_date": end.isoformat(),
                "family": family,
                "params_json": combo,
            }
            svc_task.create_task(task_type="strategy_backtest", celery_signature=None, celery_args=payload)

        push_toast("success", t("Parameter sweep queued"))
    except Exception as e:
        push_toast("error", f"{t('Failed to queue parameter sweep')}: {e}")


# --------------------------------------------------------------------------
# VISUALIZATION
# --------------------------------------------------------------------------

def _show_strategy_card(result: object, t) -> None:
    """
    Render a styled card for a backtest result.
    """
    st.markdown(f"### {result.family} — {result.ticker}")

    col1, col2 = st.columns(2)
    with col1:
        st.write(f"**{t('Start')}:** {result.start_date}")
        st.write(f"**{t('End')}:** {result.end_date}")
        st.write(f"**{t('Score')}:** {round(result.score, 4) if result.score is not None else '—'}")

    with col2:
        if st.button(t("View Chart"), key=f"chart_{result.id}"):
            _render_performance_charts(result, t)

    st.divider()
    st.dataframe(pd.DataFrame(result.metrics_json))  # Show metric table


def _render_performance_charts(result: object, t) -> None:
    """
    Render interactive time series charts for backtest results.
    """
    st.subheader(t("Equity Curve"))
    equity = pd.DataFrame(result.artifacts_json.get("equity_curve", []))
    if not equity.empty:
        st.line_chart(equity.set_index("date")["value"])
    else:
        st.info(t("No equity curve data"))

    st.subheader(t("Drawdowns"))
    drawdowns = pd.DataFrame(result.artifacts_json.get("drawdowns", []))
    if not drawdowns.empty:
        st.line_chart(drawdowns.set_index("date")["value"])
    else:
        st.info(t("No drawdown data"))

    st.subheader(t("Performance Metrics"))
    metrics = pd.DataFrame(result.metrics_json, index=[0])
    st.table(metrics)