"""Carry proxy strategy."""

from __future__ import annotations

from typing import ClassVar

from pydantic import BaseModel, Field

from quantsentinel.domain.strategies.families import build_common_metrics
from quantsentinel.domain.strategies.plugin import StrategyPlugin


class Params(BaseModel):
    signal: float
    returns: list[float] = Field(min_length=2)
    carry_strength: float = Field(default=1.0, ge=0.0)


class CarryProxyPlugin(StrategyPlugin):
    family: ClassVar[str] = "carry_proxy"
    schema: ClassVar[type[Params]] = Params
    default_params: ClassVar[dict[str, float | int | list[float]]] = {
        "signal": 1.0,
        "returns": [0.01, -0.005, 0.007, 0.003],
        "carry_strength": 1.0,
    }

    def run(self, params: Params) -> dict[str, float]:
        turnover = min(1.0, 0.35 + params.carry_strength / 3)
        return build_common_metrics(
            returns=params.returns,
            signal=params.signal,
            turnover=turnover,
            exposure_time=0.7,
            cost_impact=0.0009,
        )


plugin = CarryProxyPlugin()
