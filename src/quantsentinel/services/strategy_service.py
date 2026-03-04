"""Strategy execution service."""

from __future__ import annotations

from dataclasses import dataclass, field
from typing import Any

from quantsentinel.domain.strategies.plugin import (
    get_default_params,
    get_plugin,
    list_families,
    run_plugin,
)
from quantsentinel.domain.strategies.search import (
    BayesianSampler,
    GridSampler,
    ParameterSampler,
    RandomSampler,
    SearchDimension,
)
from quantsentinel.services.lab_contracts import LabResultView


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
        self._artifacts: list[dict[str, Any]] = []

    @property
    def families(self) -> tuple[str, ...]:
        return list_families()

    def available_families(self) -> tuple[str, ...]:
        return self.families

    def default_params(self, *, family: str) -> dict[str, Any]:
        return get_default_params(family)

    def parameter_space(self, *, family: str) -> dict[str, SearchDimension]:
        plugin = get_plugin(family)
        defaults = self.default_params(family=family)
        space: dict[str, SearchDimension] = {}

        for field_name, field_info in plugin.schema.model_fields.items():
            if field_name in {"returns", "signal"}:
                continue
            default = defaults.get(field_name)
            annotation = field_info.annotation
            if annotation is int and isinstance(default, int):
                low = max(1, int(default * 0.5))
                high = max(low + 1, int(default * 1.5))
                step = max(1, int((high - low) / 5) or 1)
                space[field_name] = SearchDimension(kind="int", low=low, high=high, step=step)
            elif annotation is float and isinstance(default, int | float):
                base = float(default)
                low = max(0.01, base * 0.5)
                high = max(low + 0.01, base * 1.5)
                step = max(0.01, (high - low) / 5)
                space[field_name] = SearchDimension(kind="float", low=low, high=high, step=step)
            elif field_info.default is not None:
                space[field_name] = SearchDimension(kind="categorical", choices=(field_info.default,))
        return space

    def build_sampler(
        self,
        *,
        sampler: str,
        space: dict[str, SearchDimension],
        seed: int | None = None,
    ) -> ParameterSampler:
        mapping: dict[str, type[ParameterSampler]] = {
            "grid": GridSampler,
            "random": RandomSampler,
            "bayesian": BayesianSampler,
        }
        key = sampler.strip().lower()
        if key not in mapping:
            raise ValueError(f"Unknown sampler: {sampler}")
        sampler_type = mapping[key]
        if sampler_type is GridSampler:
            return sampler_type(space=space)
        return sampler_type(space=space, seed=seed)

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

    def register_family_runner(self, family: str, runner: Any) -> None:
        raise NotImplementedError("Plugin-driven families do not support runtime runner overrides")

    def run(self, *, family: str, params: dict[str, Any]) -> StrategyResult:
        metrics = run_plugin(family, params)
        score = self._compute_score(metrics)

        artifact = {
            "family": family,
            "params": dict(params),
            "score": score,
            "metrics": metrics,
            "output_keys": sorted(metrics.keys()),
        }
        self._artifacts.append(artifact)

        return StrategyResult(
            family=family,
            params=dict(params),
            output=metrics,
            metrics=metrics,
            score=score,
            artifacts=[artifact],
        )

    def list_artifacts(self) -> list[dict[str, Any]]:
        return [*self._artifacts]

    def _compute_score(self, metrics: dict[str, float]) -> float:
        return round(
            (0.35 * metrics["sharpe"])
            + (0.2 * metrics["sortino"])
            + (0.2 * metrics["hit_rate"])
            + (0.15 * metrics["return"])
            - (0.1 * metrics["max_drawdown"]),
            6,
        )
