"""Pairs spread mean reversion strategy."""

from __future__ import annotations

from typing import ClassVar

from pydantic import BaseModel, Field

from quantsentinel.domain.strategies.families import build_common_metrics
from quantsentinel.domain.strategies.plugin import StrategyPlugin


class Params(BaseModel):
    signal: float
    returns: list[float] = Field(min_length=2)
    hedge_ratio: float = Field(default=1.0, gt=0.0)


class PairsSpreadMRPlugin(StrategyPlugin):
    family: ClassVar[str] = "pairs_spread_mr"
    schema: ClassVar[type[Params]] = Params
    default_params: ClassVar[dict[str, float | int | list[float]]] = {
        "signal": -0.8,
        "returns": [0.006, -0.003, 0.005, 0.002],
        "hedge_ratio": 1.0,
    }

    def run(self, params: Params) -> dict[str, float]:
        turnover = min(1.0, 0.5 + params.hedge_ratio / 4)
        return build_common_metrics(
            returns=params.returns,
            signal=params.signal,
            turnover=turnover,
            exposure_time=0.62,
            cost_impact=0.0013,
        )


plugin = PairsSpreadMRPlugin()
