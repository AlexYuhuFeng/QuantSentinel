import pytest

from quantsentinel.services.strategy_service import StrategyService


def test_strategy_service_register_and_run() -> None:
    service = StrategyService()

    service.register_family_runner(
        "ma_crossover",
        lambda _params: {
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
    assert len(service.list_artifacts()) == 1


def test_strategy_service_rejects_invalid_params() -> None:
    service = StrategyService()

    with pytest.raises(ValueError):
        service.run(family="vol_breakout", params={"signal": 1.0})


def test_strategy_service_rejects_unknown_family() -> None:
    service = StrategyService()

    with pytest.raises(ValueError):
        service.register_family_runner("unknown_family", lambda _params: {"ok": True})

    with pytest.raises(ValueError):
        service.run(family="unknown_family", params={"signal": 1.0, "returns": [0.1]})


def test_strategy_service_param_type_validation() -> None:
    service = StrategyService()

    with pytest.raises(TypeError):
        service.run(family="carry_proxy", params={"signal": "x", "returns": [0.1]})

    with pytest.raises(TypeError):
        service.run(family="carry_proxy", params={"signal": 1.0, "returns": "bad"})

    with pytest.raises(TypeError):
        service.run(family="carry_proxy", params={"signal": 1.0, "returns": [0.1, "bad"]})
