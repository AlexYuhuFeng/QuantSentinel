"""RSI mean reversion strategy."""

from __future__ import annotations

from typing import ClassVar

from pydantic import BaseModel, Field

from quantsentinel.domain.strategies.families import build_common_metrics
from quantsentinel.domain.strategies.plugin import StrategyPlugin


class Params(BaseModel):
    signal: float
    returns: list[float] = Field(min_length=2)
    rsi_low: float = Field(default=30.0, ge=0.0, le=50.0)
    rsi_high: float = Field(default=70.0, ge=50.0, le=100.0)


class RSIMeanRevertPlugin(StrategyPlugin):
    family: ClassVar[str] = "rsi_mean_revert"
    schema: ClassVar[type[Params]] = Params
    default_params: ClassVar[dict[str, float | int | list[float]]] = {
        "signal": -1.0,
        "returns": [0.007, -0.006, 0.008, 0.001],
        "rsi_low": 30.0,
        "rsi_high": 70.0,
    }

    def run(self, params: Params) -> dict[str, float]:
        spread = params.rsi_high - params.rsi_low
        turnover = min(1.0, 40 / spread) if spread else 1.0
        return build_common_metrics(
            returns=params.returns,
            signal=params.signal,
            turnover=turnover,
            exposure_time=0.55,
            cost_impact=0.0012,
        )


plugin = RSIMeanRevertPlugin()
