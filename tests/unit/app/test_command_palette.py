import sys
import types

streamlit_stub = types.SimpleNamespace(
    session_state={},
    text_input=lambda *args, **kwargs: "",
    button=lambda *args, **kwargs: False,
    rerun=lambda: None,
)
sys.modules.setdefault("streamlit", streamlit_stub)

from quantsentinel.app.ui.command_palette import CommandPalette, PaletteCommand  # noqa: E402
from quantsentinel.infra.db.models import UserRole  # noqa: E402


def _noop() -> dict[str, str]:
    return {"ok": "1"}


def _palette() -> CommandPalette:
    return CommandPalette(
        [
            PaletteCommand(
                id="open_ticker",
                label="Open ticker",
                keywords=("instrument", "symbol", "watchlist"),
                min_role=UserRole.VIEWER,
                action=_noop,
            ),
            PaletteCommand(
                id="run_backtest",
                label="Run backtest",
                keywords=("strategy", "simulation", "alpha"),
                min_role=UserRole.EDITOR,
                action=_noop,
            ),
        ]
    )


def test_fuzzy_match_finds_keyword() -> None:
    palette = _palette()

    results = palette.search_commands("symbl", UserRole.VIEWER)

    assert [command.id for command in results] == ["open_ticker"]


def test_viewer_cannot_see_high_privilege_commands() -> None:
    palette = _palette()

    visible_ids = [command.id for command in palette.visible_commands(UserRole.VIEWER)]

    assert "open_ticker" in visible_ids
    assert "run_backtest" not in visible_ids
