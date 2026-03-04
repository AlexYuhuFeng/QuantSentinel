from __future__ import annotations

import importlib
import sys
import types
from enum import Enum


def _install_streamlit_stub() -> None:
    streamlit = types.ModuleType("streamlit")
    streamlit.session_state = {}
    streamlit.query_params = {}
    streamlit.table = lambda *_args, **_kwargs: None
    streamlit.caption = lambda *_args, **_kwargs: None
    streamlit.rerun = lambda: None
    streamlit.button = lambda *_args, **_kwargs: False
    streamlit.number_input = lambda *_args, **_kwargs: 1
    streamlit.dataframe = lambda *_args, **_kwargs: None

    def _dialog(_title: str):
        def _decorate(fn):
            return fn

        return _decorate

    streamlit.dialog = _dialog

    components = types.ModuleType("streamlit.components")
    components_v1 = types.ModuleType("streamlit.components.v1")
    components_v1.html = lambda *_args, **_kwargs: None

    sys.modules["streamlit"] = streamlit
    sys.modules["streamlit.components"] = components
    sys.modules["streamlit.components.v1"] = components_v1


def _install_pandas_stub() -> None:
    pandas = types.ModuleType("pandas")

    class DataFrame:  # pragma: no cover - structural import stub
        pass

    pandas.DataFrame = DataFrame
    sys.modules["pandas"] = pandas


def _install_model_stub() -> None:
    models = types.ModuleType("quantsentinel.infra.db.models")

    class UserRole(str, Enum):
        ADMIN = "Admin"
        EDITOR = "Editor"
        VIEWER = "Viewer"

    models.UserRole = UserRole
    sys.modules["quantsentinel.infra.db.models"] = models


def _reload_modules():
    state = importlib.import_module("quantsentinel.app.ui.state")
    shortcuts = importlib.import_module("quantsentinel.app.ui.shortcuts")
    components = importlib.import_module("quantsentinel.app.ui.components")
    importlib.reload(state)
    importlib.reload(shortcuts)
    importlib.reload(components)
    return state, shortcuts, components


def test_shortcut_workspace_navigation() -> None:
    _install_streamlit_stub()
    _install_pandas_stub()
    _install_model_stub()
    state, shortcuts, _ = _reload_modules()

    state.queue_shortcut_event("goto_explore")
    shortcuts.dispatch_shortcut_events()

    assert state.ctx().workspace == "Explore"


def test_shortcut_question_mark_opens_help_dialog() -> None:
    _install_streamlit_stub()
    _install_pandas_stub()
    _install_model_stub()
    state, shortcuts, _ = _reload_modules()

    state.queue_shortcut_event("open_shortcuts_help")
    shortcuts.dispatch_shortcut_events()

    assert state.ui().shortcuts_help_open is True


def test_shortcut_slash_requests_ticker_focus() -> None:
    _install_streamlit_stub()
    _install_pandas_stub()
    _install_model_stub()
    state, shortcuts, _ = _reload_modules()

    state.queue_shortcut_event("focus_ticker")
    shortcuts.dispatch_shortcut_events()

    assert state.ui().ticker_focus_requested is True


def test_shortcut_ctrl_k_opens_command_palette() -> None:
    _install_streamlit_stub()
    _install_pandas_stub()
    _install_model_stub()
    state, shortcuts, _ = _reload_modules()

    state.queue_shortcut_event("open_command_palette")
    shortcuts.dispatch_shortcut_events()

    assert state.ui().command_palette_open is True
