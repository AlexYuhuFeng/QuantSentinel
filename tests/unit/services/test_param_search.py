from quantsentinel.domain.strategies.search import (
    BayesianSampler,
    EarlyStoppingRule,
    GridSampler,
    RandomSampler,
)
from quantsentinel.services.strategy_service import StrategyService


def test_strategy_service_parameter_space_and_samplers() -> None:
    service = StrategyService()
    space = service.parameter_space(family="ma_crossover")

    assert "fast_window" in space
    assert "slow_window" in space

    grid = service.build_sampler(sampler="grid", space=space)
    random_sampler = service.build_sampler(sampler="random", space=space, seed=123)
    bayesian = service.build_sampler(sampler="bayesian", space=space, seed=123)

    assert isinstance(grid, GridSampler)
    assert isinstance(random_sampler, RandomSampler)
    assert isinstance(bayesian, BayesianSampler)

    assert len(grid.sample(n_candidates=4)) == 4
    assert len(random_sampler.sample(n_candidates=4)) == 4


def test_early_stopping_rule() -> None:
    rule = EarlyStoppingRule(max_no_improve_rounds=3, min_delta=1e-5)

    assert rule.should_stop(scores=[0.1, 0.2, 0.25, 0.251, 0.251, 0.251, 0.251])
    assert not rule.should_stop(scores=[0.1, 0.2, 0.3, 0.31, 0.32])
