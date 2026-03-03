from __future__ import annotations

from datetime import date

import streamlit as st

from quantsentinel.app.ui.drawer import Drawer
from quantsentinel.app.ui.layout import render_workspace_shell
from quantsentinel.app.ui.state import app_state, auth, push_toast
from quantsentinel.i18n.gettext import get_translator
from quantsentinel.services.explore_service import ExploreService
from quantsentinel.services.market_service import MarketService


def render() -> None:
    t = get_translator(auth().language)
    state = app_state()
    svc_market = MarketService()
    svc_explore = ExploreService()

    def _render_toolbar() -> None:
        st.markdown(f"## {t('Explore Market Data')}")
        c1, c2, c3 = st.columns([2, 1, 1])
        with c1:
            ticker = st.text_input(t("Enter ticker"), value=state.get("explore_ticker", ""))
            state["explore_ticker"] = ticker.upper().strip()
        with c2:
            state["explore_start"] = st.date_input(
                t("Start date"), value=state.get("explore_start", date.today().replace(year=date.today().year - 1))
            )
        with c3:
            state["explore_end"] = st.date_input(t("End date"), value=state.get("explore_end", date.today()))
        if st.button(t("Refresh"), use_container_width=True):
            try:
                df = svc_market.get_price_series(
                    ticker=state["explore_ticker"],
                    start=state["explore_start"],
                    end=state["explore_end"],
                )
                state["explore_data"] = df
            except Exception as e:
                push_toast("error", f"{t('Error loading data')}: {e}")
                state["explore_data"] = None

    def _render_main() -> None:
        df = state.get("explore_data")
        if df is None:
            st.info(t("Enter a ticker and click Refresh to load data"))
            return
        if df.empty:
            st.warning(t("No price data found for the given ticker/date range"))
            return

        st.subheader(t("Price Chart"))
        st.line_chart(df.set_index("date")[["close", "open", "high", "low"]])

        st.subheader(t("Summary Statistics"))
        st.write(df.describe())

        st.subheader(t("Derived Series"))
        indicators = svc_explore.compute_indicators(df)
        for _, series in indicators.items():
            st.line_chart(series)

        if st.checkbox(t("Show raw data")):
            st.dataframe(df)

        st.success(t("Explore page loaded"))

    def _render_drawer() -> None:
        Drawer.render(title=t("Details"))

    render_workspace_shell(render_toolbar=_render_toolbar, render_main=_render_main, render_drawer=_render_drawer)
