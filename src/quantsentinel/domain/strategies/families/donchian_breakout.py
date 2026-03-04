"""Donchian breakout strategy."""

from __future__ import annotations

from typing import ClassVar

from pydantic import BaseModel, Field

from quantsentinel.domain.strategies.families import build_common_metrics
from quantsentinel.domain.strategies.plugin import StrategyPlugin


class Params(BaseModel):
    signal: float
    returns: list[float] = Field(min_length=2)
    channel_window: int = Field(default=20, gt=1)


class DonchianBreakoutPlugin(StrategyPlugin):
    family: ClassVar[str] = "donchian_breakout"
    schema: ClassVar[type[Params]] = Params
    default_params: ClassVar[dict[str, float | int | list[float]]] = {
        "signal": 1.0,
        "returns": [0.012, -0.004, 0.009, 0.002],
        "channel_window": 20,
    }

    def run(self, params: Params) -> dict[str, float]:
        turnover = min(1.0, 22 / params.channel_window)
        return build_common_metrics(
            returns=params.returns,
            signal=params.signal,
            turnover=turnover,
            exposure_time=0.8,
            cost_impact=0.001,
        )


plugin = DonchianBreakoutPlugin()
