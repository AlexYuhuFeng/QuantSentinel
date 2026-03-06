from __future__ import annotations

from collections.abc import Mapping

import streamlit as st
import streamlit.components.v1 as components

from quantsentinel.app.ui.state import (
    auth,
    pop_shortcut_event,
    queue_shortcut_event,
    set_workspace,
    ui,
)
from quantsentinel.i18n.gettext import get_translator

SHORTCUTS: dict[str, str] = {
    "g m": "Go to Market workspace",
    "g e": "Go to Explore workspace",
    "g r": "Go to Research workspace",
    "g s": "Go to Strategy workspace",
    "/": "Focus ticker search",
    "?": "Open shortcuts help",
    "Ctrl/⌘+K": "Open command palette",
}

EVENT_TO_WORKSPACE = {
    "goto_market": "Market",
    "goto_explore": "Explore",
    "goto_research": "Research",
    "goto_strategy": "Strategy",
}


def register_shortcuts(shortcuts: Mapping[str, str] | None = None) -> None:
    """Register shortcut metadata for help UI."""
    t = get_translator(auth().language)
    u = ui()
    raw_shortcuts = dict(shortcuts or SHORTCUTS)
    u.shortcuts_registry = {chord: t(description) for chord, description in raw_shortcuts.items()}
    st.session_state["qs_ui"] = u


def mount_shortcut_listener() -> None:
    """
    Mount a JS keyboard listener.

    The listener writes an encoded shortcut event into the URL query param
    `qs_shortcut`, which is read and queued server-side on the next rerun.
    """
    components.html(
        """
        <script>
        (() => {
          const parentWindow = window.parent;
          const key = "qs_shortcut_installed";
          if (parentWindow[key]) return;
          parentWindow[key] = true;

          let gPending = false;

          const emit = (eventName) => {
            const url = new URL(parentWindow.location.href);
            url.searchParams.set("qs_shortcut", `${eventName}:${Date.now()}`);
            parentWindow.location.href = url.toString();
          };

          parentWindow.addEventListener("keydown", (e) => {
            const tag = (e.target && e.target.tagName) ? e.target.tagName.toLowerCase() : "";
            const isTyping = ["input", "textarea", "select"].includes(tag) || e.target?.isContentEditable;

            if ((e.ctrlKey || e.metaKey) && e.key.toLowerCase() === "k") {
              if (isTyping) return;
              e.preventDefault();
              emit("open_command_palette");
              return;
            }

            if (!isTyping && e.key === "/") {
              e.preventDefault();
              emit("focus_ticker");
              return;
            }

            if (!isTyping && e.key === "?") {
              e.preventDefault();
              emit("open_shortcuts_help");
              return;
            }

            if (isTyping) return;

            if (e.key.toLowerCase() === "g") {
              gPending = true;
              setTimeout(() => { gPending = false; }, 800);
              return;
            }

            if (!gPending) return;

            const keymap = {
              "m": "goto_market",
              "e": "goto_explore",
              "r": "goto_research",
              "s": "goto_strategy"
            };
            const mapped = keymap[e.key.toLowerCase()];
            if (mapped) {
              e.preventDefault();
              gPending = false;
              emit(mapped);
            }
          });
        })();
        </script>
        """,
        height=0,
    )

    raw = st.query_params.get("qs_shortcut")
    if not raw:
        return

    event_name = str(raw).split(":", maxsplit=1)[0]
    queue_shortcut_event(event_name)
    st.query_params.pop("qs_shortcut")


def dispatch_shortcut_events() -> None:
    """Consume and dispatch queued shortcut events."""
    while True:
        event = pop_shortcut_event()
        if event is None:
            return
        _dispatch_single_event(event)


def _dispatch_single_event(event: str) -> None:
    current_ui = ui()

    workspace = EVENT_TO_WORKSPACE.get(event)
    if workspace is not None:
        set_workspace(workspace)
        return

    if event == "open_shortcuts_help":
        current_ui.shortcuts_help_open = True
    elif event == "focus_ticker":
        current_ui.ticker_focus_requested = True
    elif event == "open_command_palette":
        current_ui.command_palette_open = True

    st.session_state["qs_ui"] = current_ui
