import sys
import types

streamlit = types.ModuleType("streamlit")
streamlit.session_state = {}
streamlit.text_input = lambda *args, **kwargs: ""
streamlit.button = lambda *args, **kwargs: False
streamlit.rerun = lambda: None
streamlit.query_params = {}

components = types.ModuleType("streamlit.components")
components_v1 = types.ModuleType("streamlit.components.v1")
components_v1.html = lambda *args, **kwargs: None

sys.modules["streamlit"] = streamlit
sys.modules["streamlit.components"] = components
sys.modules["streamlit.components.v1"] = components_v1

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
                keyword_weights={"symbol": 1.5},
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


def test_keyword_weight_affects_ranking() -> None:
    palette = _palette()

    results = palette.search_commands("symbol", UserRole.EDITOR)

    assert results[0].id == "open_ticker"


def test_viewer_cannot_see_high_privilege_commands() -> None:
    palette = _palette()

    visible_ids = [command.id for command in palette.visible_commands(UserRole.VIEWER)]

    assert "open_ticker" in visible_ids
    assert "run_backtest" not in visible_ids
