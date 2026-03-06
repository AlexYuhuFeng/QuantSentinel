"""Alert governance helpers: dedup, silence, aggregation."""

from __future__ import annotations

from datetime import UTC, datetime

from quantsentinel.domain.alerts.models import GovernancePolicy


def should_silence(*, policy: GovernancePolicy, now: datetime | None = None) -> bool:
    """Return True when rule is inside silence window."""
    if policy.silenced_until is None:
        return False
    current = now or datetime.now(UTC)
    return policy.silenced_until > current


def resolve_aggregation_key(*, policy: GovernancePolicy, ticker: str) -> str:
    """Resolve aggregation key fallback to ticker."""
    key = (policy.aggregation_key or "").strip()
    return key or ticker


def should_dedup(
    *,
    policy: GovernancePolicy,
    rule_id,
    ticker: str,
    dedup_lookup,
) -> bool:
    """Use injected dedup lookup implementation for deterministic policy checks."""
    window = max(int(policy.dedup_minutes), 1)
    return bool(
        dedup_lookup(
            rule_id=rule_id,
            ticker=ticker,
            window_minutes=window,
            aggregation_key=policy.aggregation_key,
        )
    )
