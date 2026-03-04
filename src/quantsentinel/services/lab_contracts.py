"""Shared contracts for lab-facing service responses."""

from __future__ import annotations

from dataclasses import dataclass, field
from typing import Any


@dataclass(frozen=True)
class LabResultView:
    """Normalized result payload consumed by Strategy/Research lab pages."""

    family: str
    ticker: str
    params_json: dict[str, Any] = field(default_factory=dict)
    metrics_json: dict[str, float] = field(default_factory=dict)
    score: float = 0.0

