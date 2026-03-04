"""Research metrics."""

from __future__ import annotations

from statistics import mean, pstdev


def sharpe(returns: list[float]) -> float:
    if not returns:
        return 0.0
    avg = mean(returns)
    sigma = pstdev(returns)
    if sigma == 0:
        return 0.0
    return round(avg / sigma, 8)


def score_stability(scores: list[float]) -> float:
    """Higher is better: 1/(1+stddev) bounded in (0,1]."""
    if not scores:
        return 0.0
    sigma = pstdev(scores)
    return round(1.0 / (1.0 + sigma), 8)
