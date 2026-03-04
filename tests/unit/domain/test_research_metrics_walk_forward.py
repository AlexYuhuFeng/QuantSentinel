import pytest

from quantsentinel.domain.research.metrics import score_stability, sharpe
from quantsentinel.domain.research.walk_forward import perform


def test_sharpe_and_score_stability_are_deterministic() -> None:
    returns = [0.01, -0.02, 0.03, 0.01]
    scores = [0.4, 0.41, 0.39, 0.4]

    assert sharpe(returns) == sharpe(returns)
    assert score_stability(scores) == score_stability(scores)
    assert score_stability(scores) > 0.95


def test_walk_forward_produces_multiple_folds() -> None:
    result = perform([0.1, -0.03, 0.02, 0.01, -0.02, 0.04], folds=3)
    assert len(result) == 3
    assert result[0]["fold"] == 1


def test_walk_forward_requires_minimum_folds() -> None:
    with pytest.raises(ValueError):
        perform([0.1, 0.2], folds=1)
