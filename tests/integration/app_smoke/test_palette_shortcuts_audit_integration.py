from __future__ import annotations

import importlib
import sys
import types
import uuid
from enum import Enum


def _install_streamlit_stub() -> None:
    streamlit = types.ModuleType("streamlit")
    streamlit.session_state = {}
    streamlit.query_params = {}
    streamlit.text_input = lambda *_args, **_kwargs: ""
    streamlit.button = lambda *_args, **_kwargs: False
    streamlit.caption = lambda *_args, **_kwargs: None
    streamlit.rerun = lambda: None
    streamlit.table = lambda *_args, **_kwargs: None

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


def _reload_ui_modules():
    state = importlib.import_module("quantsentinel.app.ui.state")
    shortcuts = importlib.import_module("quantsentinel.app.ui.shortcuts")
    palette = importlib.import_module("quantsentinel.app.ui.command_palette")
    importlib.reload(state)
    importlib.reload(shortcuts)
    importlib.reload(palette)
    return state, shortcuts, palette


def test_command_visibility_changes_by_role() -> None:
    _install_streamlit_stub()
    _install_model_stub()
    _install_pandas_stub()
    state, _, palette = _reload_ui_modules()

    state.auth().role = state.UserRole.VIEWER

    app_palette = palette.CommandPalette(
        [
            palette.PaletteCommand(
                id="open_ticker",
                label="Open ticker",
                keywords=("symbol",),
                min_role=state.UserRole.VIEWER,
                action=lambda: {},
            ),
            palette.PaletteCommand(
                id="run_backtest",
                label="Run backtest",
                keywords=("strategy",),
                min_role=state.UserRole.EDITOR,
                action=lambda: {},
            ),
        ]
    )

    viewer_ids = [command.id for command in app_palette.visible_commands(state.UserRole.VIEWER)]
    editor_ids = [command.id for command in app_palette.visible_commands(state.UserRole.EDITOR)]

    assert viewer_ids == ["open_ticker"]
    assert editor_ids == ["open_ticker", "run_backtest"]


def test_command_execution_writes_audit_log_record() -> None:
    writes: list[object] = []

    engine_stub = types.ModuleType("quantsentinel.infra.db.engine")

    class FakeScope:
        def __enter__(self):
            return object()

        def __exit__(self, exc_type, exc, tb):
            return False

    engine_stub.session_scope = lambda: FakeScope()

    repo_stub = types.ModuleType("quantsentinel.infra.db.repos.audit_repo")

    class AuditEntryCreate:
        def __init__(self, *, action, entity_type, entity_id, payload, actor_id=None, ts=None):
            self.action = action
            self.entity_type = entity_type
            self.entity_id = entity_id
            self.payload = payload
            self.actor_id = actor_id
            self.ts = ts

    class FakeAuditRepo:
        def __init__(self, session) -> None:
            self._session = session

        def write(self, entry):
            writes.append(entry)

    repo_stub.AuditEntryCreate = AuditEntryCreate
    repo_stub.AuditRepo = FakeAuditRepo

    sys.modules["quantsentinel.infra.db.engine"] = engine_stub
    sys.modules["quantsentinel.infra.db.repos.audit_repo"] = repo_stub

    audit_module = importlib.import_module("quantsentinel.services.audit_service")
    importlib.reload(audit_module)

    actor_id = uuid.uuid4()
    audit_module.AuditService().log_command_palette_execution(
        actor_id=actor_id,
        command_id="refresh_data",
        payload={"source": "integration_test"},
    )

    assert len(writes) == 1
    assert writes[0].payload["command_id"] == "refresh_data"
    assert writes[0].payload["actor"] == str(actor_id)


def test_shortcut_events_change_workspace_and_dialog_state() -> None:
    _install_streamlit_stub()
    _install_model_stub()
    _install_pandas_stub()
    state, shortcuts, _ = _reload_ui_modules()

    state.queue_shortcut_event("goto_strategy")
    state.queue_shortcut_event("open_shortcuts_help")
    shortcuts.dispatch_shortcut_events()

    assert state.ctx().workspace == "Strategy"
    assert state.ui().shortcuts_help_open is True
