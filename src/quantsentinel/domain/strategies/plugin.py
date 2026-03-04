"""Strategy plugin registry and parameter validation."""

from __future__ import annotations

from typing import Any

from pydantic import BaseModel, ValidationError


class StrategyPlugin:
    family: str
    schema: type[BaseModel]
    default_params: dict[str, Any]

    def run(self, params: BaseModel) -> dict[str, float]:
        raise NotImplementedError


_REGISTRY: dict[str, StrategyPlugin] = {}


def register_plugin(plugin: StrategyPlugin) -> None:
    _REGISTRY[plugin.family] = plugin


def get_plugin(family: str) -> StrategyPlugin:
    if family not in _REGISTRY:
        raise ValueError(f"Unknown strategy family: {family}")
    return _REGISTRY[family]


def list_families() -> tuple[str, ...]:
    return tuple(sorted(_REGISTRY.keys()))


def validate_params(family: str, params: dict[str, Any]) -> BaseModel:
    plugin = get_plugin(family)
    try:
        return plugin.schema.model_validate(dict(params))
    except ValidationError as exc:
        raise ValueError(f"Invalid params for {family}: {exc.errors()}") from exc


def get_default_params(family: str) -> dict[str, Any]:
    return dict(get_plugin(family).default_params)


def run_plugin(family: str, params: dict[str, Any]) -> dict[str, float]:
    plugin = get_plugin(family)
    validated = validate_params(family, params)
    output = plugin.run(validated)
    required = {
        "return",
        "sharpe",
        "sortino",
        "max_drawdown",
        "turnover",
        "hit_rate",
        "exposure_time",
        "cost_impact",
    }
    missing = sorted(required - output.keys())
    if missing:
        raise ValueError(f"Plugin output missing metrics: {', '.join(missing)}")
    return {key: float(output[key]) for key in required}


def _bootstrap() -> None:
    from quantsentinel.domain.strategies.families.carry_proxy import plugin as carry_proxy
    from quantsentinel.domain.strategies.families.donchian_breakout import (
        plugin as donchian_breakout,
    )
    from quantsentinel.domain.strategies.families.ma_crossover import plugin as ma_crossover
    from quantsentinel.domain.strategies.families.pairs_spread_mr import plugin as pairs_spread_mr
    from quantsentinel.domain.strategies.families.rsi_mean_revert import plugin as rsi_mean_revert
    from quantsentinel.domain.strategies.families.seasonal_bias import plugin as seasonal_bias
    from quantsentinel.domain.strategies.families.vol_breakout import plugin as vol_breakout
    from quantsentinel.domain.strategies.families.zscore_mean_revert import (
        plugin as zscore_mean_revert,
    )

    for plugin in (
        carry_proxy,
        donchian_breakout,
        ma_crossover,
        pairs_spread_mr,
        rsi_mean_revert,
        seasonal_bias,
        vol_breakout,
        zscore_mean_revert,
    ):
        register_plugin(plugin)


_bootstrap()
