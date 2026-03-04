"""Volatility breakout strategy."""

from __future__ import annotations

from typing import ClassVar

from pydantic import BaseModel, Field

from quantsentinel.domain.strategies.families import build_common_metrics
from quantsentinel.domain.strategies.plugin import StrategyPlugin


class Params(BaseModel):
    signal: float
    returns: list[float] = Field(min_length=2)
    vol_multiplier: float = Field(default=1.5, gt=0)


class VolBreakoutPlugin(StrategyPlugin):
    family: ClassVar[str] = "vol_breakout"
    schema: ClassVar[type[Params]] = Params
    default_params: ClassVar[dict[str, float | int | list[float]]] = {
        "signal": 1.1,
        "returns": [0.015, -0.01, 0.011, 0.006],
        "vol_multiplier": 1.5,
    }

    def run(self, params: Params) -> dict[str, float]:
        turnover = min(1.0, 0.45 * params.vol_multiplier)
        return build_common_metrics(
            returns=params.returns,
            signal=params.signal,
            turnover=turnover,
            exposure_time=0.68,
            cost_impact=0.0016,
        )


plugin = VolBreakoutPlugin()
