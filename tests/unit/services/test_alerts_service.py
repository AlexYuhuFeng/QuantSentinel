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
        ACKED = "ACKED"

    class AlertRule:
        pass

    class UserRole:
        ADMIN = "Admin"
        EDITOR = "Editor"
        VIEWER = "Viewer"

    models.AlertEventStatus = AlertEventStatus
    models.AlertRule = AlertRule
    models.UserRole = UserRole
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

        def update_rule(self, **_kwargs):
            return None

        def delete_rule(self, **_kwargs):
            return None

        def set_rule_enabled(self, **_kwargs):
            return None

        def set_rule_silenced_until(self, **_kwargs):
            return None

    repo.AlertRuleCreate = AlertRuleCreate
    repo.AlertRuleUpdate = AlertRuleUpdate
    repo.AlertsRepo = AlertsRepo
    sys.modules["quantsentinel.infra.db.repos.alerts_repo"] = repo

    events = types.ModuleType("quantsentinel.infra.db.repos.events_repo")

    class EventsRepo:
        def __init__(self, _session):
            pass

        def ack(self, **_kwargs):
            return None

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


def test_alert_operations_write_audit() -> None:
    _install_stubs()
    module = importlib.import_module("quantsentinel.services.alerts_service")
    importlib.reload(module)

    svc = module.AlertsService()
    actor_id = uuid.uuid4()
    payload = module.AlertRuleCreate(name="r1", rule_type="threshold", params_json={"value": 1})
    role = module.UserRole.EDITOR
    svc.create_rule(actor_id=actor_id, payload=payload, actor_role=role)
    svc.update_rule(actor_id=actor_id, rule_id=uuid.uuid4(), payload=module.AlertRuleUpdate(name="r2"), actor_role=role)
    svc.delete_rule(rule_id=uuid.uuid4(), actor_id=actor_id, actor_role=role)
    svc.ack_event(event_id=uuid.uuid4(), actor_id=actor_id, actor_role=role)

    actions = [entry.action for entry in module.AuditRepo.writes]
    assert "alert_rule_create" in actions
    assert "alert_rule_update" in actions
    assert "alert_rule_delete" in actions
    assert "alert_event_ack" in actions
