import pytest

from quantsentinel.services.strategy_service import StrategyService


def test_strategy_family_matrix_has_8_families() -> None:
    svc = StrategyService()
    assert len(svc.families) == 8


@pytest.mark.parametrize("family", StrategyService().families)
def test_each_strategy_family_can_run_with_default_runner(family: str) -> None:
    svc = StrategyService()
    params = svc.default_params(family=family)

    result = svc.run(family=family, params=params)
    assert result.family == family
    assert "return" in result.output
    assert 0.0 <= result.output["hit_rate"] <= 1.0
    assert isinstance(result.score, float)


@pytest.mark.parametrize("family", StrategyService().families)
def test_each_strategy_family_rejects_invalid_params(family: str) -> None:
    svc = StrategyService()
    bad_params = svc.default_params(family=family)
    bad_params["returns"] = [0.01]

    with pytest.raises(ValueError):
        svc.run(family=family, params=bad_params)
