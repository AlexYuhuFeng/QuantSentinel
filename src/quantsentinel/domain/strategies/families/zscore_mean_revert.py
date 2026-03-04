"""Z-score mean reversion strategy."""

from __future__ import annotations

from typing import ClassVar

from pydantic import BaseModel, Field

from quantsentinel.domain.strategies.families import build_common_metrics
from quantsentinel.domain.strategies.plugin import StrategyPlugin


class Params(BaseModel):
    signal: float
    returns: list[float] = Field(min_length=2)
    entry_z: float = Field(default=2.0, gt=0.0)


class ZScoreMeanRevertPlugin(StrategyPlugin):
    family: ClassVar[str] = "zscore_mean_revert"
    schema: ClassVar[type[Params]] = Params
    default_params: ClassVar[dict[str, float | int | list[float]]] = {
        "signal": -0.9,
        "returns": [0.008, -0.007, 0.009, 0.002],
        "entry_z": 2.0,
    }

    def run(self, params: Params) -> dict[str, float]:
        turnover = min(1.0, 0.6 + (1 / (params.entry_z + 1)))
        return build_common_metrics(
            returns=params.returns,
            signal=params.signal,
            turnover=turnover,
            exposure_time=0.58,
            cost_impact=0.0014,
        )


plugin = ZScoreMeanRevertPlugin()
