"""Alert domain models shared by services and UI."""

from __future__ import annotations

from dataclasses import dataclass
from datetime import datetime
from typing import Any


@dataclass(frozen=True)
class AlertHit:
    """Represents one rule hit before it becomes an alert event."""

    message: str
    context: dict[str, Any]
    asof_date: Any | None = None


@dataclass(frozen=True)
class GovernancePolicy:
    """Execution-time governance knobs for alert creation."""

    dedup_minutes: int = 60
    aggregation_key: str | None = None
    silenced_until: datetime | None = None
