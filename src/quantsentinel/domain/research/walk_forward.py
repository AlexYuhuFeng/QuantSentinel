"""Walk-forward analysis."""

from __future__ import annotations


def perform(returns: list[float], *, folds: int) -> list[dict[str, float | int]]:
    if folds < 2:
        raise ValueError("walk-forward requires at least 2 folds")
    if not returns:
        raise ValueError("returns cannot be empty")

    fold_size = max(1, len(returns) // folds)
    out: list[dict[str, float | int]] = []
    for idx in range(folds):
        start = idx * fold_size
        end = len(returns) if idx == folds - 1 else (idx + 1) * fold_size
        segment = returns[start:end]
        if not segment:
            continue
        out.append(
            {
                "fold": idx + 1,
                "start": start,
                "end": end,
                "pnl": round(sum(segment), 8),
                "max_drawdown": round(abs(min(segment)), 8),
            }
        )

    if len(out) < 2:
        raise ValueError("insufficient data to produce >=2 folds")
    return out
