from __future__ import annotations

import streamlit as st
import streamlit.components.v1 as components

from quantsentinel.app.ui.command_palette import CommandPalette, PaletteCommand
from quantsentinel.app.ui.components import render_shortcuts_help_dialog
from quantsentinel.app.ui.notifications import render_notifications_control
from quantsentinel.app.ui.shortcuts import dispatch_shortcut_events, mount_shortcut_listener, register_shortcuts
from quantsentinel.app.ui.state import (
    auth,
    clear_auth,
    ctx,
    open_drawer,
    push_toast,
    set_authenticated,
    set_language,
    set_workspace,
    ui,
)
from quantsentinel.common.config import get_settings
from quantsentinel.infra.db.engine import db_healthcheck
from quantsentinel.infra.db.models import LayoutWorkspace, UserRole
from quantsentinel.i18n.gettext import get_translator
from quantsentinel.services.audit_service import AuditService
from quantsentinel.services.auth_service import AuthService
from quantsentinel.services.layout_service import LayoutService

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
audit_svc = AuditService()


layout_svc = LayoutService()


def _workspace_enum(value: str) -> LayoutWorkspace:
    return LayoutWorkspace(value)


def _render_layout_menu(t) -> None:
    a = auth()
    if a.user_id is None:
        return

    workspace = _workspace_enum(ctx().workspace)

    with st.popover(t("Layout"), use_container_width=False):
        can_manage = LayoutService.can_manage_layouts(a.role)
        layouts = layout_svc.load_layouts(actor_id=a.user_id, workspace=workspace)
        if layouts:
            options = [item.name for item in layouts]
            selected_name = st.selectbox(t("Preset"), options=options, key=f"layout_select_{workspace.value}")
            selected = next(item for item in layouts if item.name == selected_name)
            if st.button(t("Load default"), key=f"layout_reset_{workspace.value}"):
                layout_svc.reset_to_default(actor_id=a.user_id, workspace=workspace)
                st.success(t("Layout reset to default."))
        else:
            st.caption(t("No layout presets."))
            selected = None

        if can_manage:
            save_name = st.text_input(t("Name"), key=f"layout_name_{workspace.value}")
            if st.button(t("Save"), key=f"layout_save_{workspace.value}"):
                if save_name:
                    layout_svc.save(actor_id=a.user_id, workspace=workspace, name=save_name, layout_json={})
                    st.success(t("Layout saved."))
                    st.rerun()
            save_as_name = st.text_input(t("Save as"), key=f"layout_save_as_name_{workspace.value}")
            if st.button(t("Create preset"), key=f"layout_save_as_{workspace.value}"):
                if save_as_name:
                    layout_svc.save_as(
                        actor_id=a.user_id,
                        workspace=workspace,
                        source_layout_id=selected.layout_id if selected else None,
                        new_name=save_as_name,
                        layout_json={},
                    )
                    st.success(t("Layout preset created."))
                    st.rerun()
            if selected and st.button(t("Set default"), key=f"layout_set_default_{workspace.value}"):
                layout_svc.set_default(actor_id=a.user_id, workspace=workspace, layout_id=selected.layout_id)
                st.success(t("Default layout updated."))
                st.rerun()
            if selected and st.button(t("Delete"), key=f"layout_delete_{workspace.value}"):
                layout_svc.delete(actor_id=a.user_id, workspace=workspace, layout_id=selected.layout_id)
                st.success(t("Layout deleted."))
                st.rerun()



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




def _install_palette_shortcut_bridge() -> None:
    """Capture Ctrl/⌘+K in browser and click hidden Streamlit button."""
    components.html(
        """
        <script>
          (function () {
            if (window.__qsPaletteBound) return;
            window.__qsPaletteBound = true;
            window.parent.document.addEventListener('keydown', function (e) {
              if ((e.ctrlKey || e.metaKey) && e.key.toLowerCase() === 'k') {
                e.preventDefault();
                const btn = Array.from(window.parent.document.querySelectorAll('button'))
                  .find((item) => item.textContent && item.textContent.trim() === 'Open Command Palette');
                if (btn) btn.click();
              }
            });
          })();
        </script>
        """,
        height=0,
        width=0,
    )


def _build_command_palette() -> CommandPalette:
    def _open_ticker() -> dict[str, str]:
        open_drawer("instrument", {"ticker": "AAPL"})
        set_workspace("Market")
        return {"target": "instrument", "ticker": "AAPL"}

    def _create_rule() -> dict[str, str]:
        set_workspace("Monitor")
        open_drawer("rule_create", {"source": "command_palette"})
        return {"target": "monitor_rule_create"}

    def _run_backtest() -> dict[str, str]:
        set_workspace("Strategy")
        open_drawer("backtest", {"source": "command_palette"})
        return {"target": "strategy_backtest"}

    def _refresh_data() -> dict[str, str]:
        set_workspace("Market")
        push_toast("info", "Refresh queued from command palette.")
        return {"target": "market_refresh"}

    def _export_snapshot() -> dict[str, str]:
        push_toast("info", "Snapshot export requested from command palette.")
        return {"target": "snapshot_export"}

    def _go_workspace() -> dict[str, str]:
        set_workspace("Explore")
        return {"target": "workspace", "workspace": "Explore"}

    return CommandPalette(
        [
            PaletteCommand(
                id="open_ticker",
                label="Open ticker",
                keywords=("instrument", "symbol", "watchlist"),
                min_role=UserRole.VIEWER,
                action=_open_ticker,
            ),
            PaletteCommand(
                id="create_rule",
                label="Create rule",
                keywords=("alert", "monitor", "policy"),
                min_role=UserRole.EDITOR,
                action=_create_rule,
            ),
            PaletteCommand(
                id="run_backtest",
                label="Run backtest",
                keywords=("strategy", "simulation", "alpha"),
                min_role=UserRole.EDITOR,
                action=_run_backtest,
            ),
            PaletteCommand(
                id="refresh_data",
                label="Refresh data",
                keywords=("sync", "reload", "market"),
                min_role=UserRole.VIEWER,
                action=_refresh_data,
            ),
            PaletteCommand(
                id="export_snapshot",
                label="Export snapshot",
                keywords=("download", "report", "snapshot"),
                min_role=UserRole.VIEWER,
                action=_export_snapshot,
            ),
            PaletteCommand(
                id="go_to_workspace",
                label="Go to workspace",
                keywords=("navigate", "explore", "switch"),
                min_role=UserRole.VIEWER,
                action=_go_workspace,
            ),
        ]
    )


def _render_command_palette() -> None:
    _install_palette_shortcut_bridge()
    command_palette = _build_command_palette()
    u = ui()

    if st.button("Open Command Palette", key="open_command_palette", help="Ctrl/⌘+K"):
        u.command_palette_open = True

    if not u.command_palette_open:
        return

    with st.container(border=True):
        st.markdown("### Command Palette")

        def _on_execute(command: PaletteCommand, payload: dict[str, object]) -> None:
            audit_svc.log_command_palette_execution(
                actor_id=auth().user_id,
                command_id=command.id,
                payload={"label": command.label, **payload},
            )

        command_palette.show(on_execute=_on_execute)
        if st.button("Close palette", key="close_command_palette"):
            u.command_palette_open = False
            u.command_palette_query = ""
            st.rerun()

def main() -> None:
    a = auth()

    if not a.is_authenticated:
        render_login()
        return

    register_shortcuts()
    mount_shortcut_listener()
    dispatch_shortcut_events()

    render_header()
    _render_command_palette()
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
