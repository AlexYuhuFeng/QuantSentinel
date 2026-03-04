from quantsentinel.services.strategy_service import StrategyService


def test_strategy_family_matrix_has_8_families() -> None:
    svc = StrategyService()
    assert len(svc.families) == 8


def test_each_strategy_family_can_run_with_default_runner() -> None:
    svc = StrategyService()
    params = {"signal": 1.0, "returns": [0.03, -0.01, 0.02, 0.01]}

    for family in svc.families:
        result = svc.run(family=family, params=params)
        assert result.family == family
        assert "pnl" in result.output
        assert 0.0 <= result.output["win_rate"] <= 1.0
        assert isinstance(result.score, float)
