from __future__ import annotations

import importlib.util
import sys
from pathlib import Path
from types import ModuleType, SimpleNamespace

import pandas as pd


class _Block:
    def __enter__(self):
        return self

    def __exit__(self, exc_type, exc, tb):
        return False


class _FakeStreamlit:
    def __init__(self) -> None:
        self.subheaders: list[str] = []
        self.line_chart_calls = 0

    def markdown(self, _text: str) -> None:
        return None

    def columns(self, _spec):
        return _Block(), _Block(), _Block()

    def text_input(self, _label, value=""):
        return value or "AAPL"

    def date_input(self, _label, value):
        return value

    def button(self, _label, use_container_width=False):
        return True

    def subheader(self, text: str) -> None:
        self.subheaders.append(text)

    def line_chart(self, _data) -> None:
        self.line_chart_calls += 1

    def write(self, _data) -> None:
        return None

    def checkbox(self, _label):
        return False

    def dataframe(self, _df) -> None:
        return None

    def caption(self, _text: str) -> None:
        return None


def test_explore_page_data_flow_renders_key_charts(monkeypatch) -> None:
    fake_st = _FakeStreamlit()

    st_mod = ModuleType("streamlit")
    for attr in [
        "markdown",
        "columns",
        "text_input",
        "date_input",
        "button",
        "subheader",
        "line_chart",
        "write",
        "checkbox",
        "dataframe",
        "caption",
    ]:
        setattr(st_mod, attr, getattr(fake_st, attr))
    monkeypatch.setitem(sys.modules, "streamlit", st_mod)

    components_mod = ModuleType("quantsentinel.app.ui.components")
    components_mod.render_empty_state = lambda *_a, **_k: None
    components_mod.render_error_state = lambda *_a, **_k: None
    components_mod.render_loading_state = lambda *_a, **_k: None
    components_mod.render_success_state = lambda *_a, **_k: None
    monkeypatch.setitem(sys.modules, "quantsentinel.app.ui.components", components_mod)

    drawer_mod = ModuleType("quantsentinel.app.ui.drawer")
    drawer_mod.Drawer = SimpleNamespace(render=lambda **_kwargs: None)
    monkeypatch.setitem(sys.modules, "quantsentinel.app.ui.drawer", drawer_mod)

    layout_mod = ModuleType("quantsentinel.app.ui.layout")
    layout_mod.render_workspace_shell = (
        lambda *, render_toolbar, render_main, render_drawer: (render_toolbar(), render_main(), render_drawer())
    )
    monkeypatch.setitem(sys.modules, "quantsentinel.app.ui.layout", layout_mod)

    state_mod = ModuleType("quantsentinel.app.ui.state")
    state = {
        "explore_ticker": "AAPL",
        "explore_start": pd.Timestamp("2024-01-01").date(),
        "explore_end": pd.Timestamp("2024-01-31").date(),
    }
    state_mod.app_state = lambda: state
    state_mod.auth = lambda: SimpleNamespace(language="en", role="x")
    state_mod.push_toast = lambda *_args, **_kwargs: None
    monkeypatch.setitem(sys.modules, "quantsentinel.app.ui.state", state_mod)

    rbac_mod = ModuleType("quantsentinel.services.rbac_service")
    rbac_mod.RBACService = SimpleNamespace(can_mutate_workspace=lambda *_args, **_kwargs: True)
    monkeypatch.setitem(sys.modules, "quantsentinel.services.rbac_service", rbac_mod)

    i18n_mod = ModuleType("quantsentinel.i18n.gettext")
    i18n_mod.get_translator = lambda _lang: (lambda s: s)
    monkeypatch.setitem(sys.modules, "quantsentinel.i18n.gettext", i18n_mod)

    market_mod = ModuleType("quantsentinel.services.market_service")
    market_mod.MarketService = lambda: SimpleNamespace(
        get_price_series=lambda **_kwargs: pd.DataFrame(
            {
                "date": pd.date_range("2024-01-01", periods=25, freq="D"),
                "open": [100 + i for i in range(25)],
                "high": [101 + i for i in range(25)],
                "low": [99 + i for i in range(25)],
                "close": [100.5 + i for i in range(25)],
                "volume": [1000 + 10 * i for i in range(25)],
            }
        )
    )
    monkeypatch.setitem(sys.modules, "quantsentinel.services.market_service", market_mod)

    explore_svc_mod = ModuleType("quantsentinel.services.explore_service")
    explore_svc_mod.ExploreService = lambda: SimpleNamespace(
        compute_indicators=lambda _df: pd.DataFrame(
            {
                "date": pd.date_range("2024-01-01", periods=25, freq="D"),
                "returns": [0.0] * 25,
                "rolling_vol": [0.0] * 25,
                "zscore": [0.0] * 25,
            }
        )
    )
    monkeypatch.setitem(sys.modules, "quantsentinel.services.explore_service", explore_svc_mod)

    explore_path = Path("src/quantsentinel/app/pages/explore.py")
    spec = importlib.util.spec_from_file_location("_test_explore_page", explore_path)
    assert spec and spec.loader
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)

    module.render()

    assert "Price Chart" in fake_st.subheaders
    assert "Derived Series" in fake_st.subheaders
    assert fake_st.line_chart_calls >= 2
