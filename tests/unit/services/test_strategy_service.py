import pytest

from quantsentinel.services.strategy_service import StrategyService

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


def test_strategy_service_run_and_store_artifact() -> None:
    service = StrategyService()

    result = service.run(
        family="ma_crossover", params=service.default_params(family="ma_crossover")
    )

    assert result.family == "ma_crossover"
    assert result.score != 0
    assert set(result.output) >= REQUIRED_METRICS
    assert set(result.metrics) >= REQUIRED_METRICS
    assert "metrics" in result.artifacts[0]
    assert len(service.list_artifacts()) == 1


def test_strategy_service_rejects_invalid_params() -> None:
    service = StrategyService()

    with pytest.raises(ValueError):
        service.run(family="vol_breakout", params={"signal": 1.0})

    with pytest.raises(ValueError):
        service.run(
            family="vol_breakout",
            params={"signal": 1.0, "returns": [0.1], "vol_multiplier": -1},
        )


def test_strategy_service_rejects_unknown_family() -> None:
    service = StrategyService()

    with pytest.raises(ValueError):
        service.run(family="unknown", params={"signal": 1.0, "returns": [0.1, 0.2]})


def test_strategy_service_register_override_not_supported() -> None:
    service = StrategyService()

    with pytest.raises(NotImplementedError):
        service.register_family_runner("ma_crossover", lambda _: {})
