"""
Streamlit session state contract.

Design goals:
- Single source of truth for session keys
- Typed helpers to read/write state safely
- Prevents "stringly-typed" session_state sprawl across pages
"""

from __future__ import annotations

import uuid
from dataclasses import dataclass
from typing import Any, Literal

import streamlit as st

from quantsentinel.infra.db.models import UserRole


# -----------------------------
# Session keys (DO NOT CHANGE casually)
# -----------------------------
K_AUTH = "qs_auth"
K_CONTEXT = "qs_context"
K_UI = "qs_ui"


@dataclass
class AuthState:
    is_authenticated: bool = False
    user_id: uuid.UUID | None = None
    username: str | None = None
    role: UserRole | None = None
    language: str = "en"


@dataclass
class GlobalContext:
    ticker: str | None = None
    date_range: tuple[str, str] | None = None  # ISO yyyy-mm-dd strings for simplicity
    workspace: Literal["Market", "Explore", "Monitor", "Research", "Strategy"] = "Market"


@dataclass
class UIState:
    # Command palette
    command_palette_open: bool = False
    command_palette_query: str = ""

    # Shortcut help modal
    shortcuts_help_open: bool = False
    shortcuts_registry: dict[str, str] | None = None
    shortcut_events: list[str] | None = None
    last_shortcut_event: str | None = None

    # Ticker search focus
    ticker_focus_requested: bool = False

    # Drawer (right panel)
    drawer_open: bool = False
    drawer_kind: str | None = None
    drawer_payload: dict[str, Any] | None = None

    # Toasts / notifications (in-app)
    toast_queue: list[dict[str, Any]] | None = None


def _ensure_defaults() -> None:
    if K_AUTH not in st.session_state:
        st.session_state[K_AUTH] = AuthState()
    if K_CONTEXT not in st.session_state:
        st.session_state[K_CONTEXT] = GlobalContext()
    if K_UI not in st.session_state:
        st.session_state[K_UI] = UIState()


# -----------------------------
# Accessors
# -----------------------------

def auth() -> AuthState:
    _ensure_defaults()
    return st.session_state[K_AUTH]


def ctx() -> GlobalContext:
    _ensure_defaults()
    return st.session_state[K_CONTEXT]


def ui() -> UIState:
    _ensure_defaults()
    return st.session_state[K_UI]


# -----------------------------
# Mutators (safe updates)
# -----------------------------

def set_authenticated(
    *,
    user_id: uuid.UUID,
    username: str,
    role: UserRole,
    language: str,
) -> None:
    _ensure_defaults()
    st.session_state[K_AUTH] = AuthState(
        is_authenticated=True,
        user_id=user_id,
        username=username,
        role=role,
        language=language or "en",
    )


def clear_auth() -> None:
    _ensure_defaults()
    st.session_state[K_AUTH] = AuthState()


def set_language(language: str) -> None:
    _ensure_defaults()
    a = auth()
    a.language = language
    st.session_state[K_AUTH] = a


def set_workspace(workspace: GlobalContext.workspace.__class__ | str) -> None:
    _ensure_defaults()
    c = ctx()
    c.workspace = workspace  # type: ignore[assignment]
    st.session_state[K_CONTEXT] = c


def set_ticker(ticker: str | None) -> None:
    _ensure_defaults()
    c = ctx()
    c.ticker = ticker
    st.session_state[K_CONTEXT] = c


def open_drawer(kind: str, payload: dict[str, Any] | None = None) -> None:
    _ensure_defaults()
    u = ui()
    u.drawer_open = True
    u.drawer_kind = kind
    u.drawer_payload = payload or {}
    st.session_state[K_UI] = u


def close_drawer() -> None:
    _ensure_defaults()
    u = ui()
    u.drawer_open = False
    u.drawer_kind = None
    u.drawer_payload = None
    st.session_state[K_UI] = u


def push_toast(kind: str, message: str) -> None:
    """
    kind: 'success' | 'info' | 'warning' | 'error' (not strictly enforced here)
    """
    _ensure_defaults()
    u = ui()
    if u.toast_queue is None:
        u.toast_queue = []
    u.toast_queue.append({"kind": kind, "message": message})
    st.session_state[K_UI] = u


def queue_shortcut_event(event: str) -> None:
    _ensure_defaults()
    u = ui()
    if event == u.last_shortcut_event:
        return
    if u.shortcut_events is None:
        u.shortcut_events = []
    u.shortcut_events.append(event)
    u.last_shortcut_event = event
    st.session_state[K_UI] = u


def pop_shortcut_event() -> str | None:
    _ensure_defaults()
    u = ui()
    if not u.shortcut_events:
        return None
    event = u.shortcut_events.pop(0)
    st.session_state[K_UI] = u
    return event
