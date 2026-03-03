from __future__ import annotations

import streamlit as st

from quantsentinel.app.ui.state import open_drawer, ui
from quantsentinel.i18n.gettext import get_translator

# Services (may be placeholder now; we'll implement next)
from quantsentinel.services.market_service import MarketService


def render() -> None:
    svc = MarketService()

    # Translator
    from quantsentinel.app.ui.state import auth

    t = get_translator(auth().language)

    # -----------------------------
    # Toolbar
    # -----------------------------
    left, mid, right = st.columns([1.4, 2.2, 1.4], vertical_alignment="center")
    with left:
        st.markdown(f"## {t('Market')}")
        st.caption(t("Watchlist, anomalies, and quick context."))

    with mid:
        query = st.text_input(
            t("Quick add ticker"),
            value="",
            placeholder=t("e.g. CL=F, NG=F, AAPL"),
            label_visibility="collapsed",
        )

    with right:
        col_a, col_b = st.columns([1, 1])
        with col_a:
            refresh = st.button(t("Refresh"), use_container_width=True)
        with col_b:
            export = st.button(t("Export snapshot"), use_container_width=True)

    st.divider()

    # -----------------------------
    # Actions
    # -----------------------------
    if refresh:
        try:
            svc.refresh_watchlist_async()
            st.success(t("Refresh queued."))
        except Exception as e:
            st.error(f"{t('Failed to queue refresh')}: {e}")

    if export:
        # Snapshot/export will be implemented in snapshot service.
        st.info(t("Snapshot export is not yet wired."))
        # Keep the UX: user clicks, system responds.

    if query.strip():
        # Minimal UX: user can type ticker and click "Add" without sidebar.
        add_col1, add_col2 = st.columns([1, 5], vertical_alignment="center")
        with add_col1:
            if st.button(t("Add"), type="primary"):
                try:
                    svc.add_to_watchlist(ticker=query.strip())
                    st.success(t("Added to watchlist."))
                    st.rerun()
                except Exception as e:
                    st.error(f"{t('Failed to add')}: {e}")
        with add_col2:
            st.caption(t("Tip: Use Command Palette (Ctrl/⌘+K) to open tickers quickly."))

    # -----------------------------
    # Main layout: Watchlist + Anomalies
    # -----------------------------
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
            # Render a clean table-like list without sidebar.
            for item in watch:
                # item: expected {"ticker": str, "name": str|None, "last": float|None, "chg": float|None}
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
            for a in anomalies:
                box = st.container(border=True)
                with box:
                    st.write(f"**{a.get('title', t('Anomaly'))}**")
                    st.caption(a.get("detail", ""))
                    if st.button(t("Open"), key=f"anom_{a.get('id','')}"):
                        open_drawer("anomaly", a)
                        st.rerun()

    # -----------------------------
    # Right drawer (global UI)
    # -----------------------------
    # Keep this simple: render drawer inline for now; later we can centralize in app/ui/drawer.py
    u = ui()
    if u.drawer_open:
        with st.sidebar:
            # NOTE: We avoid using sidebar for controls, but drawer is a "detail panel" exception.
            # Later we'll move this to a proper right-side drawer component.
            st.markdown(f"### {t('Details')}")
            st.caption(f"{t('Type')}: {u.drawer_kind}")
            st.json(u.drawer_payload or {})
            if st.button(t("Close")):
                from quantsentinel.app.ui.state import close_drawer

                close_drawer()
                st.rerun()