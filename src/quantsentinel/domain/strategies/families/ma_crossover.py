"""MA crossover strategy."""

from __future__ import annotations

from typing import ClassVar

from pydantic import BaseModel, Field

from quantsentinel.domain.strategies.families import build_common_metrics
from quantsentinel.domain.strategies.plugin import StrategyPlugin


class Params(BaseModel):
    signal: float
    returns: list[float] = Field(min_length=2)
    fast_window: int = Field(default=10, gt=1)
    slow_window: int = Field(default=30, gt=2)


class MACrossoverPlugin(StrategyPlugin):
    family: ClassVar[str] = "ma_crossover"
    schema: ClassVar[type[Params]] = Params
    default_params: ClassVar[dict[str, float | int | list[float]]] = {
        "signal": 1.0,
        "returns": [0.01, -0.002, 0.006, 0.004],
        "fast_window": 10,
        "slow_window": 30,
    }

    def run(self, params: Params) -> dict[str, float]:
        turnover = min(1.0, params.fast_window / params.slow_window)
        return build_common_metrics(
            returns=params.returns,
            signal=params.signal,
            turnover=turnover,
            exposure_time=0.75,
            cost_impact=0.0008,
        )


plugin = MACrossoverPlugin()
