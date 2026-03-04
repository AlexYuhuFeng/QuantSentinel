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


def test_walk_forward_rejects_empty_returns_and_insufficient_segments() -> None:
    with pytest.raises(ValueError):
        perform([], folds=2)

    with pytest.raises(ValueError):
        perform([0.1], folds=10)


def test_sharpe_zero_for_empty_or_zero_volatility() -> None:
    assert sharpe([]) == 0.0
    assert sharpe([0.1, 0.1, 0.1]) == 0.0


def test_score_stability_zero_for_empty_scores() -> None:
    assert score_stability([]) == 0.0
