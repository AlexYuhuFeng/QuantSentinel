"""Strategy execution service."""

from __future__ import annotations

from collections.abc import Callable, Mapping
from dataclasses import dataclass, field
from statistics import mean
from typing import Any

Runner = Callable[[Mapping[str, Any]], dict[str, Any]]

_STRATEGY_FAMILIES = (
    "carry_proxy",
    "donchian_breakout",
    "ma_crossover",
    "pairs_spread_mr",
    "rsi_mean_revert",
    "seasonal_bias",
    "vol_breakout",
    "zscore_mean_revert",
)


@dataclass
class StrategyResult:
    family: str
    params: dict[str, Any]
    output: dict[str, Any]
    score: float
    artifacts: list[dict[str, Any]] = field(default_factory=list)


class StrategyService:
    """Unified strategy family registration and execution."""

    def __init__(self) -> None:
        self._runners: dict[str, Runner] = {family: self._default_runner for family in _STRATEGY_FAMILIES}
        self._artifacts: list[dict[str, Any]] = []

    @property
    def families(self) -> tuple[str, ...]:
        return _STRATEGY_FAMILIES

    def register_family_runner(self, family: str, runner: Runner) -> None:
        if family not in self._runners:
            raise ValueError(f"Unknown strategy family: {family}")
        self._runners[family] = runner

    def run(self, *, family: str, params: Mapping[str, Any]) -> StrategyResult:
        if family not in self._runners:
            raise ValueError(f"Unknown strategy family: {family}")

        self._validate_params(params)
        output = self._runners[family](params)
        score = self._compute_score(output)

        artifact = {
            "family": family,
            "params": dict(params),
            "score": score,
            "output_keys": sorted(output.keys()),
        }
        self._artifacts.append(artifact)

        return StrategyResult(
            family=family,
            params=dict(params),
            output=output,
            score=score,
            artifacts=[artifact],
        )

    def list_artifacts(self) -> list[dict[str, Any]]:
        return [*self._artifacts]

    def _validate_params(self, params: Mapping[str, Any]) -> None:
        if not params:
            raise ValueError("Strategy params are required")

        required = {"signal", "returns"}
        missing = sorted(required - set(params))
        if missing:
            joined = ", ".join(missing)
            raise ValueError(f"Missing required params: {joined}")

        if not isinstance(params["signal"], (int, float)):
            raise TypeError("param 'signal' must be numeric")

        returns = params["returns"]
        if not isinstance(returns, list) or not returns:
            raise TypeError("param 'returns' must be a non-empty list")

        if any(not isinstance(item, (int, float)) for item in returns):
            raise TypeError("all entries in 'returns' must be numeric")

    def _compute_score(self, output: Mapping[str, Any]) -> float:
        sharpe = float(output.get("sharpe", 0.0))
        drawdown = abs(float(output.get("max_drawdown", 0.0)))
        win_rate = float(output.get("win_rate", 0.0))
        return round((0.5 * sharpe) + (0.3 * win_rate) - (0.2 * drawdown), 6)

    def _default_runner(self, params: Mapping[str, Any]) -> dict[str, Any]:
        returns = [float(v) for v in params["returns"]]
        pos = sum(1 for v in returns if v > 0)
        return {
            "pnl": sum(returns),
            "sharpe": mean(returns) / (max(abs(min(returns)), abs(max(returns))) or 1.0),
            "max_drawdown": min(returns),
            "win_rate": pos / len(returns),
            "signal_used": float(params["signal"]),
        }
