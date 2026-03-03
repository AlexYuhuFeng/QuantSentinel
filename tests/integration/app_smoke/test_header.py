from __future__ import annotations

import importlib
import sys
from enum import Enum
from types import ModuleType, SimpleNamespace


class _Block:
    def __enter__(self):
        return self

    def __exit__(self, exc_type, exc, tb):
        return False


class _FakeStreamlit:
    def __init__(self) -> None:
        self.columns_calls: list[list[float]] = []
        self.captions: list[str] = []
        self.writes: list[str] = []
        self.markdowns: list[str] = []
        self.popovers: list[str] = []

    def set_page_config(self, **kwargs) -> None:
        return None

    def columns(self, spec, vertical_alignment=None):
        self.columns_calls.append(list(spec))
        return _Block(), _Block(), _Block()

    def markdown(self, text: str) -> None:
        self.markdowns.append(text)

    def caption(self, text: str) -> None:
        self.captions.append(text)

    def write(self, text: str) -> None:
        self.writes.append(text)

    def selectbox(self, label, options, index, label_visibility, key):
        return options[index]

    def popover(self, label: str, use_container_width=False):
        self.popovers.append(label)
        return _Block()

    def button(self, label: str):
        return False


def _install_main_import_stubs(monkeypatch, fake_st: _FakeStreamlit) -> None:
    monkeypatch.setitem(sys.modules, "streamlit", fake_st)

    state_mod = ModuleType("quantsentinel.app.ui.state")
    state_mod.auth = lambda: SimpleNamespace(language="en", user_id=None, username="alice")
    state_mod.ctx = lambda: SimpleNamespace(ticker="AAPL", date_label="2026-01-01 → 2026-01-31", workspace="Research")
    state_mod.clear_auth = lambda: None
    state_mod.set_authenticated = lambda **kwargs: None
    state_mod.set_language = lambda language: None
    state_mod.set_workspace = lambda workspace: None
    monkeypatch.setitem(sys.modules, "quantsentinel.app.ui.state", state_mod)

    notif_mod = ModuleType("quantsentinel.app.ui.notifications")
    notif_mod.render_notifications_control = lambda t: None
    monkeypatch.setitem(sys.modules, "quantsentinel.app.ui.notifications", notif_mod)

    cfg_mod = ModuleType("quantsentinel.common.config")
    cfg_mod.get_settings = lambda: SimpleNamespace()
    monkeypatch.setitem(sys.modules, "quantsentinel.common.config", cfg_mod)

    db_engine_mod = ModuleType("quantsentinel.infra.db.engine")
    db_engine_mod.db_healthcheck = lambda: {"status": "ok"}
    monkeypatch.setitem(sys.modules, "quantsentinel.infra.db.engine", db_engine_mod)

    db_models_mod = ModuleType("quantsentinel.infra.db.models")

    class _UserRole(str, Enum):
        ADMIN = "admin"

    db_models_mod.UserRole = _UserRole
    monkeypatch.setitem(sys.modules, "quantsentinel.infra.db.models", db_models_mod)

    auth_svc_mod = ModuleType("quantsentinel.services.auth_service")
    auth_svc_mod.AuthService = lambda: SimpleNamespace(set_default_language=lambda **kwargs: None)
    monkeypatch.setitem(sys.modules, "quantsentinel.services.auth_service", auth_svc_mod)

    pages_pkg = ModuleType("quantsentinel.app.pages")
    for name in ["admin", "explore", "help", "market", "monitor", "research_lab", "strategy_lab"]:
        setattr(pages_pkg, name, SimpleNamespace(render=lambda: None))
    monkeypatch.setitem(sys.modules, "quantsentinel.app.pages", pages_pkg)


def test_render_header_has_three_regions_and_context_without_role(monkeypatch) -> None:
    fake_st = _FakeStreamlit()
    _install_main_import_stubs(monkeypatch, fake_st)

    main = importlib.import_module("quantsentinel.app.main")
    main.render_header()

    assert fake_st.columns_calls == [[1.2, 2.6, 1.2]]
    assert "Ticker | Date | Workspace" in fake_st.captions
    assert "AAPL | 2026-01-01 → 2026-01-31 | Research" in fake_st.writes
    assert all("Role" not in text for text in fake_st.writes)
    assert any("User menu" in label for label in fake_st.popovers)
