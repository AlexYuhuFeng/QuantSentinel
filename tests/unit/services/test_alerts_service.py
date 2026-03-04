from __future__ import annotations

import importlib
import sys
import types
import uuid
from dataclasses import dataclass


def _install_stubs() -> None:
    engine = types.ModuleType("quantsentinel.infra.db.engine")

    class Scope:
        def __enter__(self):
            return object()

        def __exit__(self, exc_type, exc, tb):
            return False

    engine.session_scope = lambda: Scope()
    sys.modules["quantsentinel.infra.db.engine"] = engine

    models = types.ModuleType("quantsentinel.infra.db.models")

    class AlertEventStatus:
        NEW = "NEW"

    class AlertRule:
        pass

    models.AlertEventStatus = AlertEventStatus
    models.AlertRule = AlertRule
    sys.modules["quantsentinel.infra.db.models"] = models

    repo = types.ModuleType("quantsentinel.infra.db.repos.alerts_repo")

    @dataclass
    class AlertRuleCreate:
        name: str
        rule_type: str
        params_json: dict

    @dataclass
    class AlertRuleUpdate:
        name: str | None = None

    class AlertsRepo:
        def __init__(self, _session):
            pass

        def create_rule(self, _payload):
            return uuid.uuid4()

        def list_enabled_rules(self):
            return []

    repo.AlertRuleCreate = AlertRuleCreate
    repo.AlertRuleUpdate = AlertRuleUpdate
    repo.AlertsRepo = AlertsRepo
    sys.modules["quantsentinel.infra.db.repos.alerts_repo"] = repo

    events = types.ModuleType("quantsentinel.infra.db.repos.events_repo")

    class EventsRepo:
        def __init__(self, _session):
            pass

    events.EventsRepo = EventsRepo
    sys.modules["quantsentinel.infra.db.repos.events_repo"] = events

    audit = types.ModuleType("quantsentinel.infra.db.repos.audit_repo")

    @dataclass
    class AuditEntryCreate:
        action: str
        entity_type: str
        entity_id: str | None
        actor_id: uuid.UUID | None
        payload: dict
        ts: object

    class AuditRepo:
        writes = []

        def __init__(self, _session):
            pass

        def write(self, entry):
            AuditRepo.writes.append(entry)

    audit.AuditEntryCreate = AuditEntryCreate
    audit.AuditRepo = AuditRepo
    sys.modules["quantsentinel.infra.db.repos.audit_repo"] = audit

    for name, cls_name in [
        ("quantsentinel.infra.db.repos.instruments_repo", "InstrumentsRepo"),
        ("quantsentinel.infra.db.repos.prices_repo", "PricesRepo"),
        ("quantsentinel.services.task_service", "TaskService"),
        ("quantsentinel.domain.alerts.expression", "evaluate"),
    ]:
        mod = types.ModuleType(name)
        if cls_name == "evaluate":
            mod.evaluate = lambda *_a, **_k: True
        elif cls_name == "InstrumentsRepo":
            mod.InstrumentsRepo = type("InstrumentsRepo", (), {"__init__": lambda self, _s: None, "list_watched": lambda self: []})
        elif cls_name == "PricesRepo":
            mod.PricesRepo = type("PricesRepo", (), {"__init__": lambda self, _s: None})
        else:
            mod.TaskService = type("TaskService", (), {})
        sys.modules[name] = mod


def test_create_rule_writes_audit() -> None:
    _install_stubs()
    module = importlib.import_module("quantsentinel.services.alerts_service")
    importlib.reload(module)

    svc = module.AlertsService()
    payload = module.AlertRuleCreate(name="r1", rule_type="threshold", params_json={"value": 1})
    svc.create_rule(actor_id=uuid.uuid4(), payload=payload)

    assert len(module.AuditRepo.writes) == 1
    assert module.AuditRepo.writes[0].action == "alert_rule_create"
