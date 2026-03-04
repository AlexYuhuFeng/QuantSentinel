from __future__ import annotations

from dataclasses import dataclass
from difflib import SequenceMatcher
from typing import Callable

import streamlit as st

from quantsentinel.app.ui.state import auth, ui
from quantsentinel.i18n.gettext import get_translator
from quantsentinel.infra.db.models import UserRole

_ROLE_WEIGHT = {
    UserRole.VIEWER: 1,
    UserRole.EDITOR: 2,
    UserRole.ADMIN: 3,
}


@dataclass(frozen=True)
class PaletteCommand:
    id: str
    label: str
    keywords: tuple[str, ...]
    min_role: UserRole
    action: Callable[[], dict[str, object] | None]


class CommandPalette:
    def __init__(self, commands: list[PaletteCommand]) -> None:
        self._commands = list(commands)

    def visible_commands(self, role: UserRole | None) -> list[PaletteCommand]:
        if role is None:
            return []
        actor_weight = _ROLE_WEIGHT.get(role, 0)
        return [
            command
            for command in self._commands
            if actor_weight >= _ROLE_WEIGHT.get(command.min_role, 99)
        ]

    def search_commands(self, query: str, role: UserRole | None) -> list[PaletteCommand]:
        visible = self.visible_commands(role)
        if not query.strip():
            return visible

        scored: list[tuple[float, PaletteCommand]] = []
        needle = query.lower().strip()
        for command in visible:
            haystacks = [command.label.lower(), *(word.lower() for word in command.keywords)]
            score = max(SequenceMatcher(None, needle, term).ratio() for term in haystacks)
            if score >= 0.45:
                scored.append((score, command))

        scored.sort(key=lambda pair: pair[0], reverse=True)
        return [command for _, command in scored]

    def show(
        self,
        *,
        on_execute: Callable[[PaletteCommand, dict[str, object]], None] | None = None,
    ) -> None:
        translator = get_translator(auth().language)
        app_ui = ui()
        query = st.text_input(
            translator("Command palette..."),
            value=app_ui.command_palette_query,
            key="qs_command_palette_query",
        )
        app_ui.command_palette_query = query

        results = self.search_commands(query, auth().role)
        if not results:
            st.caption(translator("No matching commands."))
            return

        for command in results:
            if st.button(command.label, key=f"cmd_{command.id}"):
                payload = command.action() or {}
                if on_execute is not None:
                    on_execute(command, payload)
                app_ui.command_palette_open = False
                st.rerun()
