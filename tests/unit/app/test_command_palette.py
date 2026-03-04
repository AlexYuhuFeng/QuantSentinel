import sys
import types

def _text_input(*_args, **_kwargs) -> str:
    return ""


def _button(*_args, **_kwargs) -> bool:
    return False


def _rerun() -> None:
    return


streamlit_stub = types.ModuleType("streamlit")
streamlit_stub.session_state = {}
streamlit_stub.text_input = _text_input
streamlit_stub.button = _button
streamlit_stub.rerun = _rerun

streamlit_components = types.ModuleType("streamlit.components")
streamlit_components_v1 = types.ModuleType("streamlit.components.v1")
streamlit_components.v1 = streamlit_components_v1
streamlit_stub.components = streamlit_components

sys.modules.setdefault("streamlit", streamlit_stub)
sys.modules.setdefault("streamlit.components", streamlit_components)
sys.modules.setdefault("streamlit.components.v1", streamlit_components_v1)

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
