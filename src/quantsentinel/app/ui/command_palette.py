from __future__ import annotations

from dataclasses import dataclass
from difflib import SequenceMatcher
from typing import TYPE_CHECKING

import streamlit as st

from quantsentinel.app.ui.state import auth, ui
from quantsentinel.i18n.gettext import get_translator
from quantsentinel.infra.db.models import UserRole

if TYPE_CHECKING:
    from collections.abc import Callable

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
    keyword_weights: dict[str, float] | None = None


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
            score = self._score_command(command, needle)
            if score >= 0.40:
                scored.append((score, command))

        scored.sort(key=lambda pair: pair[0], reverse=True)
        return [command for _, command in scored]

    @staticmethod
    def _score_term(needle: str, term: str) -> float:
        ratio = SequenceMatcher(None, needle, term).ratio()
        if term.startswith(needle):
            ratio += 0.25
        elif needle in term:
            ratio += 0.12
        return min(ratio, 1.0)

    def _score_command(self, command: PaletteCommand, needle: str) -> float:
        label_score = self._score_term(needle, command.label.lower()) * 1.5
        keyword_scores = [
            self._score_term(needle, keyword.lower()) * self._keyword_weight(command, keyword)
            for keyword in command.keywords
        ]
        best_keyword_score = max(keyword_scores, default=0.0)
        return max(label_score, best_keyword_score)

    @staticmethod
    def _keyword_weight(command: PaletteCommand, keyword: str) -> float:
        if command.keyword_weights is not None and keyword in command.keyword_weights:
            return max(command.keyword_weights[keyword], 0.1)
        length = len(keyword.strip())
        if length <= 4:
            return 1.2
        if length <= 8:
            return 1.0
        return 0.9

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
