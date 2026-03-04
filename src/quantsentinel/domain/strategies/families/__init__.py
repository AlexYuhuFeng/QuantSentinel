"""Built-in strategy family plugins."""

from __future__ import annotations

from statistics import mean, pstdev


def _safe_pstdev(values: list[float]) -> float:
    return pstdev(values) if len(values) > 1 else 0.0


def _max_drawdown(returns: list[float]) -> float:
    equity = 1.0
    peak = 1.0
    max_dd = 0.0
    for ret in returns:
        equity *= 1.0 + ret
        peak = max(peak, equity)
        drawdown = (peak - equity) / peak if peak else 0.0
        max_dd = max(max_dd, drawdown)
    return max_dd


def build_common_metrics(
    *,
    returns: list[float],
    signal: float,
    turnover: float,
    exposure_time: float,
    cost_impact: float,
) -> dict[str, float]:
    clean_returns = [float(v) for v in returns]
    avg = mean(clean_returns)
    sigma = _safe_pstdev(clean_returns)
    downside = _safe_pstdev([r for r in clean_returns if r < 0])
    hit_rate = sum(1 for r in clean_returns if r > 0) / len(clean_returns)

    gross_return = sum(clean_returns) * abs(signal)
    sharpe = (avg / sigma) if sigma else 0.0
    sortino = (avg / downside) if downside else 0.0

    return {
        "return": round(gross_return, 8),
        "sharpe": round(sharpe, 8),
        "sortino": round(sortino, 8),
        "max_drawdown": round(_max_drawdown(clean_returns), 8),
        "turnover": round(turnover, 8),
        "hit_rate": round(hit_rate, 8),
        "exposure_time": round(max(0.0, min(1.0, exposure_time)), 8),
        "cost_impact": round(cost_impact, 8),
    }
