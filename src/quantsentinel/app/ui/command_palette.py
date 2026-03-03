from __future__ import annotations

from dataclasses import dataclass
from difflib import SequenceMatcher
from typing import Any, Callable

import streamlit as st

from quantsentinel.app.ui.state import auth, ui
from quantsentinel.infra.db.models import UserRole


RoleAction = Callable[[], dict[str, Any] | None]


@dataclass(frozen=True)
class PaletteCommand:
    id: str
    label: str
    keywords: tuple[str, ...]
    min_role: UserRole
    action: RoleAction


_ROLE_ORDER: dict[UserRole, int] = {
    UserRole.VIEWER: 0,
    UserRole.EDITOR: 1,
    UserRole.ADMIN: 2,
}


class CommandPalette:
    """Role-aware command palette with fuzzy matching."""

    def __init__(self, commands: list[PaletteCommand] | None = None) -> None:
        self._commands: dict[str, PaletteCommand] = {c.id: c for c in (commands or [])}

    def register(self, command: PaletteCommand) -> None:
        self._commands[command.id] = command

    def visible_commands(self, role: UserRole | None) -> list[PaletteCommand]:
        if role is None:
            return []
        role_rank = _ROLE_ORDER[role]
        return [
            command
            for command in self._commands.values()
            if _ROLE_ORDER[command.min_role] <= role_rank
        ]

    def search_commands(self, query: str, role: UserRole | None) -> list[PaletteCommand]:
        candidates = self.visible_commands(role)
        stripped = query.strip().lower()
        if not stripped:
            return candidates

        scored: list[tuple[float, PaletteCommand]] = []
        for command in candidates:
            score = _fuzzy_score(stripped, command)
            if score > 0.33:
                scored.append((score, command))

        scored.sort(key=lambda item: item[0], reverse=True)
        return [command for _, command in scored]

    def execute(self, command_id: str) -> tuple[PaletteCommand, dict[str, Any] | None]:
        command = self._commands[command_id]
        payload = command.action() or {}
        return command, payload

    def show(
        self,
        *,
        on_execute: Callable[[PaletteCommand, dict[str, Any]], None] | None = None,
    ) -> None:
        u = ui()
        current_role = auth().role
        query = st.text_input("Command palette...", value=u.command_palette_query)
        u.command_palette_query = query

        for command in self.search_commands(query, current_role):
            if st.button(command.label, key=f"palette_cmd_{command.id}"):
                executed, payload = self.execute(command.id)
                if on_execute is not None:
                    on_execute(executed, payload)
                u.command_palette_open = False
                u.command_palette_query = ""
                st.rerun()


def _fuzzy_score(query: str, command: PaletteCommand) -> float:
    terms = [command.label.lower(), *[kw.lower() for kw in command.keywords]]

    best_ratio = max(SequenceMatcher(None, query, term).ratio() for term in terms)
    token_boost = 1.0 if any(query in token for token in terms) else 0.0
    return (best_ratio * 0.75) + (token_boost * 0.25)
