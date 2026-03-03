from __future__ import annotations

import streamlit as st

from quantsentinel.app.ui.state import auth, clear_auth, ctx, set_authenticated, set_language, set_workspace
from quantsentinel.services.layout_service import LayoutService
from quantsentinel.infra.db.models import LayoutWorkspace
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
    st.title("QuantSentinel")
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
                    username="admin",
                    email="admin@example.com",
                    password="admin12345",
                    default_language=auth().language,
                )
                st.success(t("Bootstrap admin created. You can sign in now."))
            except Exception as e:
                st.error(f"{t('Bootstrap failed')}: {e}")

    with col2:
        st.info(
            t("Default bootstrap credentials (after bootstrap): admin / admin12345. Please change password immediately.")
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

    left, mid, right = st.columns([1.2, 2.6, 1.2], vertical_alignment="center")
    with left:
        st.markdown("### QuantSentinel")

    with mid:
        # Global context placeholder (ticker/date/workspace)
        st.caption(t("Terminal context"))
        st.write(f"**{t('Workspace')}**: {ctx().workspace}")
        _render_layout_menu(t)

    with right:
        lang = st.selectbox(
            t("Language"),
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

        with st.popover("👤", use_container_width=False):
            st.write(f"**{a.username or ''}**")
            st.caption(f"{t('Role')}: {a.role.value if a.role else '-'}")
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

    render_header()
    page_key = render_sidebar()
    render_page(page_key)


if __name__ == "__main__":
    main()