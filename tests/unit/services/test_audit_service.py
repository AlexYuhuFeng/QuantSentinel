import uuid

from quantsentinel.services.audit_service import AuditService


def test_command_palette_execution_writes_audit_log(monkeypatch) -> None:
    writes: list[object] = []

    class FakeAuditRepo:
        def __init__(self, session) -> None:
            self._session = session

        def write(self, entry):
            writes.append(entry)

    class FakeScope:
        def __enter__(self):
            return object()

        def __exit__(self, exc_type, exc, tb):
            return False

    monkeypatch.setattr("quantsentinel.services.audit_service.AuditRepo", FakeAuditRepo)
    monkeypatch.setattr("quantsentinel.services.audit_service.session_scope", lambda: FakeScope())

    actor_id = uuid.uuid4()
    svc = AuditService()
    svc.log_command_palette_execution(
        actor_id=actor_id,
        command_id="open_ticker",
        payload={"source": "unit_test"},
    )

    assert len(writes) == 1
    entry = writes[0]
    assert entry.action == "command_palette_execute"
    assert entry.entity_id == "open_ticker"
    assert entry.actor_id == actor_id
    assert entry.payload["command_id"] == "open_ticker"
    assert entry.payload["source"] == "unit_test"



def test_command_palette_audit_payload_includes_actor_id(monkeypatch) -> None:
    writes: list[object] = []

    class FakeAuditRepo:
        def __init__(self, session) -> None:
            self._session = session

        def write(self, entry):
            writes.append(entry)

    class FakeScope:
        def __enter__(self):
            return object()

        def __exit__(self, exc_type, exc, tb):
            return False

    monkeypatch.setattr("quantsentinel.services.audit_service.AuditRepo", FakeAuditRepo)
    monkeypatch.setattr("quantsentinel.services.audit_service.session_scope", lambda: FakeScope())

    actor_id = uuid.uuid4()
    AuditService().log_command_palette_execution(actor_id=actor_id, command_id="refresh_data", payload={})

    assert writes[0].payload["actor_id"] == str(actor_id)
