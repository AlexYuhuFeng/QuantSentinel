import pytest

from quantsentinel.services.strategy_service import StrategyService


def test_strategy_service_register_and_run() -> None:
    service = StrategyService()

    service.register_family_runner(
        "ma_crossover",
        lambda params: {
            "sharpe": 1.4,
            "max_drawdown": -0.1,
            "win_rate": 0.6,
            "pnl": 0.12,
        },
    )

    result = service.run(family="ma_crossover", params={"signal": 1.0, "returns": [0.1, -0.02, 0.04]})

    assert result.family == "ma_crossover"
    assert result.score > 0
    assert result.output["pnl"] == 0.12
    assert "metrics" in result.artifacts[0]
    assert result.metrics["sharpe"] == 1.4
    assert len(service.list_artifacts()) == 1


def test_strategy_service_rejects_invalid_params() -> None:
    service = StrategyService()

    with pytest.raises(ValueError):
        service.run(family="vol_breakout", params={"signal": 1.0})

    with pytest.raises(TypeError):
        service.run(family="vol_breakout", params={"signal": "up", "returns": [0.1]})

    with pytest.raises(TypeError):
        service.run(family="vol_breakout", params={"signal": 1.0, "returns": [0.1, "x"]})


def test_strategy_service_rejects_unknown_family() -> None:
    service = StrategyService()

    with pytest.raises(ValueError):
        service.register_family_runner("unknown", lambda _: {})

    with pytest.raises(ValueError):
        service.run(family="unknown", params={"signal": 1.0, "returns": [0.1]})
