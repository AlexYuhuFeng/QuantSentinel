"""
QuantSentinel Streamlit entrypoint (UI scaffold).

Clean rule:
- This file is executed ONLY by Streamlit:
  `streamlit run src/quantsentinel/app/main.py`

Design rule:
- Do NOT import unfinished services/infra/domain here yet.
- Keep this as a stable UI shell so docker-compose can boot from day 1.
"""

from __future__ import annotations

import os
import socket
from dataclasses import dataclass
from typing import Dict, Optional
from urllib.parse import urlparse

import streamlit as st


# -----------------------------------------------------------------------------
# Bootstrap i18n (temporary)
# Replace later with gettext-based quantsentinel.i18n implementation.
# -----------------------------------------------------------------------------
I18N: Dict[str, Dict[str, str]] = {
    "en": {
        "app_name": "QuantSentinel",
        "login": "Login",
        "username": "Username",
        "password": "Password",
        "sign_in": "Sign in",
        "sign_out": "Sign out",
        "invalid_creds": "Invalid credentials.",
        "workspace": "Workspace",
        "market": "Market",
        "explore": "Explore",
        "monitor": "Monitor",
        "research": "Research Lab",
        "strategy": "Strategy Lab",
        "admin": "Admin",
        "help": "Help",
        "system_status": "System Status",
        "db": "Database",
        "redis": "Redis",
        "ok": "OK",
        "down": "DOWN",
        "unknown": "UNKNOWN",
        "command_palette": "Command Palette",
        "run_command": "Run",
        "shortcuts": "Shortcuts",
        "shortcuts_hint": "Keyboard shortcuts require a custom Streamlit component. Placeholder only.",
        "layout": "Layout",
        "save_layout": "Save layout",
        "load_layout": "Load layout",
        "preset_name": "Preset name",
        "saved": "Saved.",
        "not_implemented": "Not implemented yet (scaffold).",
        "role": "Role",
        "language": "Language",
        "default_admin_note": "Default admin (bootstrap): admin / Admin123! (override via env)",
    },
    "zh_CN": {
        "app_name": "QuantSentinel",
        "login": "登录",
        "username": "用户名",
        "password": "密码",
        "sign_in": "登录",
        "sign_out": "退出登录",
        "invalid_creds": "用户名或密码错误。",
        "workspace": "工作台",
        "market": "市场",
        "explore": "分析",
        "monitor": "监控",
        "research": "研究实验室",
        "strategy": "策略实验室",
        "admin": "管理",
        "help": "帮助",
        "system_status": "系统状态",
        "db": "数据库",
        "redis": "Redis",
        "ok": "正常",
        "down": "不可用",
        "unknown": "未知",
        "command_palette": "命令面板",
        "run_command": "执行",
        "shortcuts": "快捷键",
        "shortcuts_hint": "键盘快捷键需要自定义 Streamlit 组件，这里先做 UI 占位。",
        "layout": "布局",
        "save_layout": "保存布局",
        "load_layout": "加载布局",
        "preset_name": "预设名称",
        "saved": "已保存。",
        "not_implemented": "尚未实现（脚手架阶段）。",
        "role": "角色",
        "language": "语言",
        "default_admin_note": "默认管理员（启动阶段）：admin / Admin123!（可通过环境变量覆盖）",
    },
}


def t(key: str) -> str:
    lang = st.session_state.get("lang", "en")
    return I18N.get(lang, I18N["en"]).get(key, key)


# -----------------------------------------------------------------------------
# Bootstrap auth (temporary)
# Replace later with DB-backed users + Argon2 + RBAC.
# -----------------------------------------------------------------------------
@dataclass(frozen=True)
class User:
    username: str
    role: str


def _bootstrap_admin_creds() -> tuple[str, str]:
    u = os.getenv("QS_DEFAULT_ADMIN_USER", "admin")
    p = os.getenv("QS_DEFAULT_ADMIN_PASSWORD", "Admin123!")
    return u, p


def check_login(username: str, password: str) -> Optional[User]:
    admin_u, admin_p = _bootstrap_admin_creds()
    if username == admin_u and password == admin_p:
        return User(username=username, role="Admin")
    return None


# -----------------------------------------------------------------------------
# Lightweight connectivity checks (TCP only)
# -----------------------------------------------------------------------------
def _tcp_health(url: str) -> str:
    if not url:
        return t("unknown")
    try:
        u = urlparse(url)
        host = u.hostname
        port = u.port
        if not host or not port:
            return t("unknown")
        with socket.create_connection((host, port), timeout=0.8):
            return t("ok")
    except Exception:
        return t("down")


# -----------------------------------------------------------------------------
# UI shell
# -----------------------------------------------------------------------------
def header_bar(workspace: str) -> None:
    left, mid, right = st.columns([1.3, 3.2, 1.5], vertical_alignment="center")

    with left:
        st.markdown(
            f"<div style='font-size:20px;font-weight:700;'>{t('app_name')}</div>",
            unsafe_allow_html=True,
        )

    with mid:
        ticker = st.session_state.get("ctx_ticker", "—")
        date_range = st.session_state.get("ctx_range", "1Y")
        source = st.session_state.get("ctx_source", "—")
        st.markdown(
            f"""
            <div style="opacity:0.85;">
              <b>{t("workspace")}:</b> {workspace} &nbsp;|&nbsp;
              <b>Ticker:</b> {ticker} &nbsp;|&nbsp;
              <b>Range:</b> {date_range} &nbsp;|&nbsp;
              <b>Source:</b> {source}
            </div>
            """,
            unsafe_allow_html=True,
        )

    with right:
        user: Optional[User] = st.session_state.get("user")
        role = user.role if user else "—"
        lang = st.session_state.get("lang", "en")

        c1, c2, c3 = st.columns([1, 1, 1], vertical_alignment="center")
        with c1:
            st.selectbox(
                t("language"),
                options=["en", "zh_CN"],
                index=0 if lang == "en" else 1,
                key="lang",
                label_visibility="collapsed",
            )
        with c2:
            st.caption(f"{t('role')}: **{role}**")
        with c3:
            if user and st.button(t("sign_out"), use_container_width=True):
                st.session_state["user"] = None
                st.rerun()


def sidebar_nav() -> str:
    with st.sidebar:
        st.caption(t("system_status"))

        db_url = os.getenv("DATABASE_URL", "")
        redis_url = os.getenv("REDIS_URL", os.getenv("CELERY_BROKER_URL", ""))

        st.write(f"**{t('db')}**: {_tcp_health(db_url)}")
        st.write(f"**{t('redis')}**: {_tcp_health(redis_url)}")
        st.divider()

        user: Optional[User] = st.session_state.get("user")
        role = user.role if user else "Viewer"

        items = [t("market"), t("explore"), t("monitor"), t("research"), t("strategy"), t("help")]
        if role == "Admin":
            # If you prefer strict <=6, merge Admin into Help later.
            items.insert(5, t("admin"))

        choice = st.radio(t("workspace"), items, key="nav", label_visibility="collapsed")
        return choice


def login_screen() -> None:
    st.markdown(f"## {t('login')}")
    st.info(t("default_admin_note"))

    with st.form("login", clear_on_submit=False):
        username = st.text_input(t("username"), value="")
        password = st.text_input(t("password"), type="password", value="")
        submitted = st.form_submit_button(t("sign_in"), use_container_width=True)

    if submitted:
        user = check_login(username.strip(), password)
        if user is None:
            st.error(t("invalid_creds"))
            return
        st.session_state["user"] = user
        st.rerun()


# -----------------------------------------------------------------------------
# Workspace placeholders (real content will be wired to services later)
# -----------------------------------------------------------------------------
def _placeholder(title_key: str, next_hint: str) -> None:
    st.subheader(t(title_key))
    st.write(t("not_implemented"))
    st.caption(next_hint)


def page_market() -> None:
    _placeholder("market", "Next: watchlist table + anomalies panel + right-side drawer.")


def page_explore() -> None:
    _placeholder("explore", "Next: multi-panel Plotly chart + QC + derived + snapshot export.")


def page_monitor() -> None:
    _placeholder("monitor", "Next: rule wizard + governance (dedup/silence/aggregate) + events view.")


def page_research() -> None:
    _placeholder("research", "Next: projects + runs compare + walk-forward + artifacts.")


def page_strategy() -> None:
    _placeholder("strategy", "Next: strategy plugins + search (grid/random/bayes) + leaderboard + drawer.")


def page_admin() -> None:
    _placeholder("admin", "Next: users/RBAC + audit log viewer + system settings.")


def page_help() -> None:
    st.subheader(t("help"))
    st.markdown(
        f"""
- **{t("command_palette")}** and **{t("layout")}** are UI stubs for now.
- This file is intentionally isolated from unfinished layers to keep the app bootable.
        """
    )
    with st.expander(t("shortcuts"), expanded=True):
        st.write(t("shortcuts_hint"))
        st.code(
            "g m -> Market\n"
            "g e -> Explore\n"
            "g r -> Research Lab\n"
            "g s -> Strategy Lab\n"
            "/   -> Search ticker\n"
            "?   -> Shortcut help\n",
            language="text",
        )


def command_palette_ui() -> None:
    # Real Ctrl/⌘+K requires a Streamlit component; this is an interactive placeholder.
    with st.popover(t("command_palette")):
        cmd = st.text_input("Search command", placeholder="Open ticker / Refresh / Export snapshot ...")
        if st.button(t("run_command"), use_container_width=True):
            st.toast(f"Command received: {cmd!r}", icon="🧭")


def layout_presets_ui() -> None:
    # Real DB-backed presets will live in ui_layout_presets; this is a placeholder.
    with st.popover(t("layout")):
        name = st.text_input(t("preset_name"), value="default")
        c1, c2 = st.columns(2)
        with c1:
            if st.button(t("save_layout"), use_container_width=True):
                st.session_state.setdefault("_layout_presets", {})[name] = {
                    "version": 1,
                    "nav": st.session_state.get("nav"),
                    "ctx_ticker": st.session_state.get("ctx_ticker"),
                    "ctx_range": st.session_state.get("ctx_range"),
                }
                st.success(t("saved"))
        with c2:
            if st.button(t("load_layout"), use_container_width=True):
                preset = st.session_state.get("_layout_presets", {}).get(name)
                if preset:
                    st.session_state["nav"] = preset.get("nav", st.session_state.get("nav"))
                    st.session_state["ctx_ticker"] = preset.get("ctx_ticker", st.session_state.get("ctx_ticker"))
                    st.session_state["ctx_range"] = preset.get("ctx_range", st.session_state.get("ctx_range"))
                    st.rerun()
                st.info(t("saved"))


def run_streamlit_app() -> None:
    st.set_page_config(page_title="QuantSentinel", layout="wide")

    # defaults
    st.session_state.setdefault("lang", os.getenv("QS_DEFAULT_LOCALE", "en"))
    st.session_state.setdefault("ctx_ticker", "—")
    st.session_state.setdefault("ctx_range", "1Y")
    st.session_state.setdefault("ctx_source", "—")

    if st.session_state.get("user") is None:
        login_screen()
        return

    nav = sidebar_nav()
    header_bar(workspace=nav)

    # main-area utility buttons
    right_util = st.columns([4, 1])[1]
    with right_util:
        c1, c2 = st.columns(2)
        with c1:
            command_palette_ui()
        with c2:
            layout_presets_ui()

    st.divider()

    # routing
    if nav == t("market"):
        page_market()
    elif nav == t("explore"):
        page_explore()
    elif nav == t("monitor"):
        page_monitor()
    elif nav == t("research"):
        page_research()
    elif nav == t("strategy"):
        page_strategy()
    elif nav == t("admin"):
        page_admin()
    else:
        page_help()


if __name__ == "__main__":
    run_streamlit_app()