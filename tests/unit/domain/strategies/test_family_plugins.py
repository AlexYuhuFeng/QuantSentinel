import pytest

from quantsentinel.domain.strategies.plugin import list_families, run_plugin

REQUIRED_METRICS = {
    "return",
    "sharpe",
    "sortino",
    "max_drawdown",
    "turnover",
    "hit_rate",
    "exposure_time",
    "cost_impact",
}


@pytest.mark.parametrize("family", list_families())
def test_family_plugin_runs_with_valid_params(family: str) -> None:
    base = {
        "signal": 1.0,
        "returns": [0.01, -0.02, 0.03],
        "fast_window": 5,
        "slow_window": 20,
        "channel_window": 10,
        "rsi_low": 25,
        "rsi_high": 75,
        "entry_z": 2,
        "vol_multiplier": 1.2,
        "hedge_ratio": 1.0,
        "active_months": 6,
        "carry_strength": 1.0,
    }

    metrics = run_plugin(family, base)
    assert set(metrics) == REQUIRED_METRICS


@pytest.mark.parametrize("family", list_families())
def test_family_plugin_rejects_invalid_params(family: str) -> None:
    with pytest.raises(ValueError):
        run_plugin(family, {"signal": 1.0, "returns": [0.01]})
