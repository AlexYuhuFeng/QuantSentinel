from __future__ import annotations

from datetime import UTC, datetime, timedelta
from uuid import uuid4

from quantsentinel.domain.alerts.governance import (
    resolve_aggregation_key,
    should_dedup,
    should_silence,
)
from quantsentinel.domain.alerts.models import GovernancePolicy


def test_should_silence_when_window_active() -> None:
    now = datetime.now(UTC)
    policy = GovernancePolicy(silenced_until=now + timedelta(minutes=10))
    assert should_silence(policy=policy, now=now) is True


def test_resolve_aggregation_key_falls_back_to_ticker() -> None:
    policy = GovernancePolicy(aggregation_key=None)
    assert resolve_aggregation_key(policy=policy, ticker="AAPL") == "AAPL"


def test_should_dedup_uses_policy_window_and_key() -> None:
    captured = {}

    def _lookup(**kwargs):
        captured.update(kwargs)
        return True

    rule_id = uuid4()
    policy = GovernancePolicy(dedup_minutes=15, aggregation_key="tech-bucket")
    assert should_dedup(policy=policy, rule_id=rule_id, ticker="MSFT", dedup_lookup=_lookup) is True
    assert captured["window_minutes"] == 15
    assert captured["aggregation_key"] == "tech-bucket"
