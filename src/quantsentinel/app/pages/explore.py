from __future__ import annotations

import streamlit as st
from datetime import date
from typing import Optional

from quantsentinel.app.ui.state import auth, app_state, push_toast
from quantsentinel.i18n.gettext import get_translator
from quantsentinel.services.market_service import MarketService
from quantsentinel.services.explore_service import ExploreService
from quantsentinel.infra.db.repos.prices_repo import PriceDaily

# ----------------------------------------------------------------------------
# Explore Page — interactive data explorer + charts + filters
# ----------------------------------------------------------------------------

def render() -> None:
    """
    Explore page — visualize market price data, derived indicators,
    filters, and time selectors.
    """
    a = auth()
    t = get_translator(a.language)

    st.markdown(f"## {t('Explore Market Data')}")

    # Input: ticker selector
    ticker = st.text_input(t("Enter ticker"), value=app_state.get("explore_ticker", ""))

    if ticker:
        app_state["explore_ticker"] = ticker.upper().strip()

    # Date range selection
    col1, col2 = st.columns(2)
    with col1:
        start = st.date_input(t("Start date"), value=app_state.get("explore_start", date.today().replace(year=date.today().year - 1)))
        app_state["explore_start"] = start
    with col2:
        end = st.date_input(t("End date"), value=app_state.get("explore_end", date.today()))
        app_state["explore_end"] = end

    if ticker and start > end:
        st.error(t("Start date must be before end date"))
        return

    svc_market = MarketService()
    svc_explore = ExploreService()

    # Load price data when user submits
    if st.button(t("Refresh")):
        if not ticker:
            st.warning(t("Please enter a ticker"))
        else:
            with st.spinner(t("Fetching data...")):
                try:
                    df = svc_market.get_price_series(ticker=ticker, start=start, end=end)
                    app_state["explore_data"] = df
                except Exception as e:
                    push_toast("error", f"{t('Error loading data')}: {e}")
                    app_state["explore_data"] = None

    df = app_state.get("explore_data", None)

    if df is None:
        st.info(t("Enter a ticker and click Refresh to load data"))
        return

    if df.empty:
        st.warning(t("No price data found for the given ticker/date range"))
        return

    # Show price chart
    st.subheader(t("Price Chart"))
    st.line_chart(df.set_index("date")[["close", "open", "high", "low"]])

    # Show simple statistics
    st.subheader(t("Summary Statistics"))
    st.write(df.describe())

    # Derived indicators
    st.subheader(t("Derived Series"))
    indicators = svc_explore.compute_indicators(df)

    for name, series in indicators.items():
        st.line_chart(series)

    # Optionally show raw data
    if st.checkbox(t("Show raw data")):
        st.dataframe(df)

    st.success(t("Explore page loaded"))