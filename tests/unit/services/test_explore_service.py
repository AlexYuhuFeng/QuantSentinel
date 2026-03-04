from __future__ import annotations

import math

import pandas as pd
import pytest

from quantsentinel.services.explore_service import ExploreService


def test_compute_indicators_requires_date_and_close() -> None:
    svc = ExploreService()

    with pytest.raises(ValueError, match="Missing required columns"):
        svc.compute_indicators(pd.DataFrame({"close": [1, 2, 3]}))


def test_compute_indicators_returns_expected_columns_for_empty_df() -> None:
    svc = ExploreService()
    out = svc.compute_indicators(pd.DataFrame(columns=["date", "close"]))

    assert list(out.columns) == ["date", "returns", "rolling_vol", "zscore"]
    assert out.empty


def test_compute_indicators_values() -> None:
    svc = ExploreService()
    closes = [100 + i for i in range(25)]
    df = pd.DataFrame(
        {
            "date": pd.date_range("2024-01-01", periods=25, freq="D"),
            "close": closes,
        }
    )

    out = svc.compute_indicators(df)

    expected_last_return = (124 / 123) - 1
    assert out.iloc[-1]["returns"] == pytest.approx(expected_last_return)

    window_returns = [(closes[i] / closes[i - 1]) - 1 for i in range(5, 25)]
    expected_vol = pd.Series(window_returns).std(ddof=0)
    assert out.iloc[-1]["rolling_vol"] == pytest.approx(expected_vol)

    window_closes = closes[-20:]
    mean_close = sum(window_closes) / len(window_closes)
    variance = sum((c - mean_close) ** 2 for c in window_closes) / len(window_closes)
    expected_z = (closes[-1] - mean_close) / math.sqrt(variance)
    assert out.iloc[-1]["zscore"] == pytest.approx(expected_z)
