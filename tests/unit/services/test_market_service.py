from __future__ import annotations

from datetime import date
from types import SimpleNamespace

import pandas as pd
import pytest

from quantsentinel.services import market_service as mod


class _Expr:
    def __eq__(self, _other):
        return self

    def __ge__(self, _other):
        return self

    def __le__(self, _other):
        return self

    def asc(self):
        return self


class _FakeStmt:
    def where(self, *_args, **_kwargs):
        return self

    def order_by(self, *_args, **_kwargs):
        return self


class _Scope:
    def __init__(self, rows):
        self._rows = rows

    def __enter__(self):
        return SimpleNamespace(execute=lambda _stmt: SimpleNamespace(all=lambda: self._rows))

    def __exit__(self, exc_type, exc, tb):
        return False


def _install_query_stubs(monkeypatch, rows):
    monkeypatch.setattr(mod, "PriceDaily", SimpleNamespace(date=_Expr(), open=_Expr(), high=_Expr(), low=_Expr(), close=_Expr(), volume=_Expr(), ticker=_Expr()))
    monkeypatch.setattr(mod, "select", lambda *_args, **_kwargs: _FakeStmt())
    monkeypatch.setattr(mod, "session_scope", lambda: _Scope(rows))


def test_get_price_series_validates_ticker_and_date_range() -> None:
    svc = mod.MarketService()

    with pytest.raises(ValueError, match="Ticker required"):
        svc.get_price_series(ticker=" ", start=date(2024, 1, 1), end=date(2024, 1, 10))

    with pytest.raises(ValueError, match="Start date must be <= end date"):
        svc.get_price_series(ticker="AAPL", start=date(2024, 1, 10), end=date(2024, 1, 1))


def test_get_price_series_empty_result_has_expected_columns(monkeypatch) -> None:
    _install_query_stubs(monkeypatch, rows=[])

    svc = mod.MarketService()
    df = svc.get_price_series(ticker="aapl", start=date(2024, 1, 1), end=date(2024, 1, 5))

    assert list(df.columns) == ["date", "open", "high", "low", "close", "volume"]
    assert df.empty


def test_get_price_series_returns_dataframe_rows(monkeypatch) -> None:
    rows = [
        (date(2024, 1, 1), 100.0, 101.0, 99.0, 100.5, 1000),
        (date(2024, 1, 2), 101.0, 103.0, 100.0, 102.5, 1200),
    ]
    _install_query_stubs(monkeypatch, rows=rows)

    svc = mod.MarketService()
    df = svc.get_price_series(ticker="AAPL", start=date(2024, 1, 1), end=date(2024, 1, 2))

    assert isinstance(df, pd.DataFrame)
    assert df.to_dict(orient="records") == [
        {"date": date(2024, 1, 1), "open": 100.0, "high": 101.0, "low": 99.0, "close": 100.5, "volume": 1000},
        {"date": date(2024, 1, 2), "open": 101.0, "high": 103.0, "low": 100.0, "close": 102.5, "volume": 1200},
    ]
