"""Seasonal bias strategy."""

from __future__ import annotations

from typing import ClassVar

from pydantic import BaseModel, Field

from quantsentinel.domain.strategies.families import build_common_metrics
from quantsentinel.domain.strategies.plugin import StrategyPlugin


class Params(BaseModel):
    signal: float
    returns: list[float] = Field(min_length=2)
    active_months: int = Field(default=6, ge=1, le=12)


class SeasonalBiasPlugin(StrategyPlugin):
    family: ClassVar[str] = "seasonal_bias"
    schema: ClassVar[type[Params]] = Params
    default_params: ClassVar[dict[str, float | int | list[float]]] = {
        "signal": 0.6,
        "returns": [0.005, -0.001, 0.004, 0.003],
        "active_months": 6,
    }

    def run(self, params: Params) -> dict[str, float]:
        exposure = params.active_months / 12
        turnover = min(1.0, 0.25 + exposure)
        return build_common_metrics(
            returns=params.returns,
            signal=params.signal,
            turnover=turnover,
            exposure_time=exposure,
            cost_impact=0.0006,
        )


plugin = SeasonalBiasPlugin()
