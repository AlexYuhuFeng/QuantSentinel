"""Strategy execution service."""

from __future__ import annotations

from collections.abc import Callable, Mapping
from dataclasses import dataclass, field
from statistics import mean, pstdev
from typing import Any

from quantsentinel.services.lab_contracts import LabResultView

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

_DEFAULT_PARAMS: dict[str, dict[str, Any]] = {
    "carry_proxy": {"signal": 1.0, "returns": [0.01, -0.005, 0.007, 0.003]},
    "donchian_breakout": {"signal": 1.0, "returns": [0.012, -0.004, 0.009, 0.002]},
    "ma_crossover": {"signal": 1.0, "returns": [0.01, -0.002, 0.006, 0.004]},
    "pairs_spread_mr": {"signal": -0.8, "returns": [0.006, -0.003, 0.005, 0.002]},
    "rsi_mean_revert": {"signal": -1.0, "returns": [0.007, -0.006, 0.008, 0.001]},
    "seasonal_bias": {"signal": 0.6, "returns": [0.005, -0.001, 0.004, 0.003]},
    "vol_breakout": {"signal": 1.1, "returns": [0.015, -0.01, 0.011, 0.006]},
    "zscore_mean_revert": {"signal": -0.9, "returns": [0.008, -0.007, 0.009, 0.002]},
}


@dataclass
class StrategyResult:
    family: str
    params: dict[str, Any]
    output: dict[str, Any]
    metrics: dict[str, float]
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

    def available_families(self) -> tuple[str, ...]:
        return self.families

    def default_params(self, *, family: str) -> dict[str, Any]:
        if family not in self._runners:
            raise ValueError(f"Unknown strategy family: {family}")
        return dict(_DEFAULT_PARAMS[family])

    def get_recent_results(self, *, limit: int = 20) -> list[LabResultView]:
        if limit <= 0:
            return []
        recent = list(reversed(self._artifacts))[:limit]
        return [
            LabResultView(
                family=str(artifact.get("family", "unknown")),
                ticker=str(artifact.get("ticker", "N/A")),
                params_json=dict(artifact.get("params", {})),
                metrics_json=dict(artifact.get("metrics", {})),
                score=float(artifact.get("score", 0.0)),
            )
            for artifact in recent
        ]

    def register_family_runner(self, family: str, runner: Runner) -> None:
        if family not in self._runners:
            raise ValueError(f"Unknown strategy family: {family}")
        self._runners[family] = runner

    def run(self, *, family: str, params: Mapping[str, Any]) -> StrategyResult:
        if family not in self._runners:
            raise ValueError(f"Unknown strategy family: {family}")

        self._validate_params(params)
        output = self._runners[family](params)
        metrics = self._build_metrics(output, params)
        score = self._compute_score(metrics)

        artifact = {
            "family": family,
            "params": dict(params),
            "score": score,
            "metrics": metrics,
            "output_keys": sorted(output.keys()),
        }
        self._artifacts.append(artifact)

        return StrategyResult(
            family=family,
            params=dict(params),
            output=output,
            metrics=metrics,
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

    def _build_metrics(self, output: Mapping[str, Any], params: Mapping[str, Any]) -> dict[str, float]:
        returns = [float(v) for v in params["returns"]]
        sharpe = float(output.get("sharpe", self._sharpe(returns)))
        drawdown = abs(float(output.get("max_drawdown", min(returns))))
        win_rate = float(output.get("win_rate", sum(1 for v in returns if v > 0) / len(returns)))

        volatility = pstdev(returns) if len(returns) > 1 else 0.0
        total_pnl = float(output.get("pnl", sum(returns)))

        return {
            "pnl": round(total_pnl, 8),
            "sharpe": round(sharpe, 8),
            "max_drawdown": round(drawdown, 8),
            "win_rate": round(win_rate, 8),
            "volatility": round(volatility, 8),
        }

    def _compute_score(self, metrics: Mapping[str, float]) -> float:
        return round(
            (0.45 * metrics["sharpe"])
            + (0.25 * metrics["win_rate"])
            + (0.2 * metrics["pnl"])
            - (0.1 * metrics["max_drawdown"]),
            6,
        )

    def _sharpe(self, returns: list[float]) -> float:
        sigma = pstdev(returns) if len(returns) > 1 else 0.0
        if sigma == 0:
            return 0.0
        return mean(returns) / sigma

    def _default_runner(self, params: Mapping[str, Any]) -> dict[str, Any]:
        returns = [float(v) for v in params["returns"]]
        pos = sum(1 for v in returns if v > 0)
        return {
            "pnl": sum(returns),
            "sharpe": self._sharpe(returns),
            "max_drawdown": min(returns),
            "win_rate": pos / len(returns),
            "signal_used": float(params["signal"]),
        }
