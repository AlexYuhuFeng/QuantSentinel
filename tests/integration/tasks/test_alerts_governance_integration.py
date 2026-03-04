from __future__ import annotations

from dataclasses import dataclass
from datetime import datetime, timedelta, timezone
from types import SimpleNamespace
from uuid import uuid4

from quantsentinel.services.alerts_service import AlertsService


@dataclass
class _Rule:
    id: object
    name: str
    rule_type: str
    params_json: dict
    scope_json: dict
    silenced_until: datetime | None


@dataclass
class _Watched:
    ticker: str


class _FakeScope:
    def __enter__(self):
        return object()

    def __exit__(self, exc_type, exc, tb):
        return False


def test_run_monitor_cycle_applies_silence_dedup_and_aggregation(monkeypatch) -> None:
    now = datetime.now(timezone.utc)
    silenced_rule = _Rule(
        id=uuid4(),
        name="silenced",
        rule_type="threshold",
        params_json={"operator": ">", "value": 50, "dedup_minutes": 10},
        scope_json={"tickers": ["AAA"]},
        silenced_until=now + timedelta(minutes=10),
    )
    active_rule = _Rule(
        id=uuid4(),
        name="active",
        rule_type="threshold",
        params_json={"operator": ">", "value": 50, "dedup_minutes": 10, "aggregation_key": "group-1"},
        scope_json={"tickers": ["BBB"]},
        silenced_until=None,
    )

    created = []

    class AlertsRepoStub:
        def __init__(self, _session):
            pass

        def list_enabled_rules(self):
            return [silenced_rule, active_rule]

    class EventsRepoStub:
        def __init__(self, _session):
            pass

        def exists_recent(self, **kwargs):
            return kwargs.get("ticker") == "BBB"

        def create_event(self, **kwargs):
            created.append(kwargs)

    class InstRepoStub:
        def __init__(self, _session):
            pass

        def list_watched(self):
            return [_Watched("AAA"), _Watched("BBB")]

    class PricesRepoStub:
        def __init__(self, _session):
            pass

        def get_latest_close(self, *, ticker: str):
            return now.date(), 100.0

    class AuditRepoStub:
        writes = []

        def __init__(self, _session):
            pass

        def write(self, entry):
            self.writes.append(entry)

    monkeypatch.setattr("quantsentinel.services.alerts_service.session_scope", lambda: _FakeScope())
    monkeypatch.setattr("quantsentinel.services.alerts_service.AlertsRepo", AlertsRepoStub)
    monkeypatch.setattr("quantsentinel.services.alerts_service.EventsRepo", EventsRepoStub)
    monkeypatch.setattr("quantsentinel.services.alerts_service.InstrumentsRepo", InstRepoStub)
    monkeypatch.setattr("quantsentinel.services.alerts_service.PricesRepo", PricesRepoStub)
    monkeypatch.setattr("quantsentinel.services.alerts_service.AuditRepo", AuditRepoStub)
    monkeypatch.setattr("quantsentinel.services.alerts_service.TaskService", lambda: SimpleNamespace(set_progress=lambda **_kwargs: None))

    result = AlertsService().run_monitor_cycle(actor_id=None, task_id=None)

    assert result["events_silenced"] == 1
    assert result["events_deduped"] == 1
    assert result["events_created"] == 0
    assert any(item.action == "alert_rule_run" for item in AuditRepoStub.writes)
    assert created == []
