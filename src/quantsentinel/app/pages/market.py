from __future__ import annotations

import streamlit as st

from quantsentinel.app.ui.drawer import Drawer
from quantsentinel.app.ui.layout import render_workspace_shell
from quantsentinel.app.ui.state import auth, open_drawer
from quantsentinel.i18n.gettext import get_translator
from quantsentinel.services.market_service import MarketService


def render() -> None:
    svc = MarketService()
    t = get_translator(auth().language)
    page_state: dict[str, object] = {"query": "", "refresh": False, "export": False}

    def _render_toolbar() -> None:
        left, mid, right = st.columns([1.4, 2.2, 1.4], vertical_alignment="center")
        with left:
            st.markdown(f"## {t('Market')}")
            st.caption(t("Watchlist, anomalies, and quick context."))
        with mid:
            page_state["query"] = st.text_input(
                t("Quick add ticker"),
                value="",
                placeholder=t("e.g. CL=F, NG=F, AAPL"),
                label_visibility="collapsed",
            )
        with right:
            a, b = st.columns(2)
            with a:
                page_state["refresh"] = st.button(t("Refresh"), use_container_width=True)
            with b:
                page_state["export"] = st.button(t("Export snapshot"), use_container_width=True)

    def _render_main() -> None:
        refresh = bool(page_state["refresh"])
        export = bool(page_state["export"])
        query = str(page_state["query"])

        if refresh:
            try:
                svc.refresh_watchlist_async()
                st.success(t("Refresh queued."))
            except Exception as e:
                st.error(f"{t('Failed to queue refresh')}: {e}")
        if export:
            st.info(t("Snapshot export is not yet wired."))

        if query.strip():
            add_l, add_r = st.columns([1, 5], vertical_alignment="center")
            with add_l:
                if st.button(t("Add"), type="primary"):
                    try:
                        svc.add_to_watchlist(ticker=query.strip())
                        st.success(t("Added to watchlist."))
                        st.rerun()
                    except Exception as e:
                        st.error(f"{t('Failed to add')}: {e}")
            with add_r:
                st.caption(t("Tip: Use Command Palette (Ctrl/⌘+K) to open tickers quickly."))

        col_left, col_right = st.columns([1.7, 1.3], gap="large")
        with col_left:
            st.subheader(t("Watchlist"))
            try:
                watch = svc.get_watchlist()
            except Exception:
                watch = []
            if not watch:
                st.info(t("Your watchlist is empty. Add a ticker above."))
            else:
                for item in watch:
                    row = st.container(border=True)
                    with row:
                        a, b, c, d = st.columns([1.0, 1.7, 1.0, 0.8], vertical_alignment="center")
                        with a:
                            st.markdown(f"**{item.get('ticker', '')}**")
                            if item.get("name"):
                                st.caption(item["name"])
                        with b:
                            st.caption(t("Last"))
                            st.write(item.get("last", "—"))
                        with c:
                            st.caption(t("Change"))
                            st.write(item.get("chg", "—"))
                        with d:
                            if st.button("⋯", key=f"watch_more_{item.get('ticker','')}", help=t("Details")):
                                open_drawer("instrument", {"ticker": item.get("ticker")})
                                st.rerun()

        with col_right:
            st.subheader(t("Anomalies"))
            st.caption(t("Auto scans for volatility spikes, correlation breaks, stale data, etc."))
            try:
                anomalies = svc.get_anomalies()
            except Exception:
                anomalies = []
            if not anomalies:
                st.info(t("No anomalies detected (or data not loaded)."))
            else:
                for anomaly in anomalies:
                    box = st.container(border=True)
                    with box:
                        st.write(f"**{anomaly.get('title', t('Anomaly'))}**")
                        st.caption(anomaly.get("detail", ""))
                        if st.button(t("Open"), key=f"anom_{anomaly.get('id','')}"):
                            open_drawer("anomaly", anomaly)
                            st.rerun()

    def _render_drawer() -> None:
        Drawer.render(title=t("Details"))

    render_workspace_shell(render_toolbar=_render_toolbar, render_main=_render_main, render_drawer=_render_drawer)
