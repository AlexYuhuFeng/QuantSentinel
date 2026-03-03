from __future__ import annotations

import streamlit as st
import streamlit.components.v1 as components

from quantsentinel.app.ui.notifications import render_notifications_control
from quantsentinel.app.ui.state import auth, clear_auth, ctx, set_authenticated, set_language, set_workspace
from quantsentinel.common.config import get_settings
from quantsentinel.infra.db.engine import db_healthcheck
from quantsentinel.infra.db.models import UserRole
from quantsentinel.i18n.gettext import get_translator
from quantsentinel.services.auth_service import AuthService

from quantsentinel.app.pages import (
    admin,
    explore,
    help as help_page,
    market,
    monitor,
    research_lab,
    strategy_lab,
)

# -----------------------------
# App config
# -----------------------------
st.set_page_config(page_title="QuantSentinel", layout="wide")

settings = get_settings()
auth_svc = AuthService()


def _t():
    """Convenience: current translator based on session language."""
    a = auth()
    return get_translator(a.language)


def render_login() -> None:
    t = _t()
    st.title(t("QuantSentinel"))
    st.caption(t("Team Edition trading research terminal"))

    with st.form("login_form", clear_on_submit=False):
        identifier = st.text_input(t("Username or email"), value="")
        password = st.text_input(t("Password"), value="", type="password")
        submitted = st.form_submit_button(t("Sign in"))

    col1, col2 = st.columns([1, 2], vertical_alignment="center")
    with col1:
        if st.button(t("Bootstrap admin")):
            # This is safe: it only creates admin if DB has no users.
            try:
                auth_svc.ensure_default_admin(
                    username=settings.default_admin_username,
                    email=settings.default_admin_email,
                    password=settings.default_admin_password,
                    default_language=settings.default_admin_language,
                )
                st.success(t("Bootstrap admin created. You can sign in now."))
            except Exception as e:
                st.error(f"{t('Bootstrap failed')}: {e}")

    with col2:
        st.info(
            t(
                "Default bootstrap credentials (after bootstrap): "
                f"{settings.default_admin_username} / {settings.default_admin_password} "
                f"(language: {settings.default_admin_language}). Please change password immediately."
            )
        )

    if submitted:
        res = auth_svc.login(identifier=identifier, password=password)
        if not res.ok or res.user_id is None or res.role is None:
            st.error(res.error or t("Invalid credentials."))
            return
        set_authenticated(
            user_id=res.user_id,
            username=res.username or "",
            role=res.role,
            language=res.default_language or auth().language,
        )
        st.rerun()


def render_header() -> None:
    t = _t()
    a = auth()
    c = ctx()

    left, mid, right = st.columns([1.2, 2.6, 1.2], vertical_alignment="center")
    with left:
        st.markdown(f"### {t('QuantSentinel')}")

    with mid:
        ticker_label = c.ticker or "-"
        date_label = c.date_label or "-"
        workspace_label = c.workspace or "-"
        st.caption(t("Ticker | Date | Workspace"))
        st.write(f"{ticker_label} | {date_label} | {workspace_label}")

    with right:
        render_notifications_control(t)

        lang = st.selectbox(
            t("Language switch"),
            options=["en", "zh_CN"],
            index=0 if a.language == "en" else 1,
            label_visibility="collapsed",
            key="qs_lang_select",
        )
        if lang != a.language:
            set_language(lang)
            # Persist preference for logged-in users
            if a.user_id is not None:
                try:
                    auth_svc.set_default_language(actor_id=a.user_id, user_id=a.user_id, language=lang)
                except Exception:
                    # Don't block UX on persistence failure
                    pass
            st.rerun()

        with st.popover(f"👤 {t('User menu')}", use_container_width=False):
            st.write(f"**{a.username or ''}**")
            if st.button(t("Sign out")):
                clear_auth()
                st.rerun()


def render_sidebar() -> str:
    t = _t()
    a = auth()

    with st.sidebar:
        st.markdown("## " + t("Navigation"))

        # Role-based visibility
        pages = [
            ("Market", t("Market")),
            ("Explore", t("Explore")),
            ("Monitor", t("Monitor")),
            ("Research", t("Research Lab")),
            ("Strategy", t("Strategy Lab")),
        ]
        if a.role == UserRole.ADMIN:
            pages.append(("Admin", t("Admin")))

        label_to_key = {label: key for key, label in pages}
        selected_label = st.radio(
            label=t("Workspaces"),
            options=[label for _, label in pages],
            index=0,
        )
        selected = label_to_key[selected_label]

        st.divider()
        st.caption(t("System health"))
        db_stat = db_healthcheck()
        st.write(f"DB: **{db_stat.get('status')}**")
        if db_stat.get("status") != "ok":
            st.code(db_stat.get("detail", ""), language="text")

        st.caption(t("Tips"))
        st.write(t("Use Ctrl/⌘+K for Command Palette. Press ? for shortcuts."))

    return selected


def render_page(page_key: str) -> None:
    """
    Route to a workspace page module. Each page is responsible for its own toolbar/body/drawer.
    """
    if page_key == "Market":
        set_workspace("Market")
        market.render()
    elif page_key == "Explore":
        set_workspace("Explore")
        explore.render()
    elif page_key == "Monitor":
        set_workspace("Monitor")
        monitor.render()
    elif page_key == "Research":
        set_workspace("Research")
        research_lab.render()
    elif page_key == "Strategy":
        set_workspace("Strategy")
        strategy_lab.render()
    elif page_key == "Admin":
        set_workspace("Market")
        admin.render()
    else:
        help_page.render()


def main() -> None:
    a = auth()

    if not a.is_authenticated:
        render_login()
        return

    register_shortcuts()
    mount_shortcut_listener()
    dispatch_shortcut_events()

    render_header()
    page_key = render_sidebar()
    render_page(page_key)
    render_shortcuts_help_dialog()


def _consume_ticker_focus_request() -> None:
    if not st.session_state.get("qs_ui"):
        return

    app_ui = st.session_state["qs_ui"]
    if not app_ui.ticker_focus_requested:
        return

    components.html(
        """
        <script>
        const root = window.parent.document;
        const input = root.querySelector('input[aria-label="Ticker"]');
        if (input) input.focus();
        </script>
        """,
        height=0,
    )
    app_ui.ticker_focus_requested = False
    st.session_state["qs_ui"] = app_ui


if __name__ == "__main__":
    main()
