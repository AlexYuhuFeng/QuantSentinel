from __future__ import annotations

import uuid
from contextlib import contextmanager

from quantsentinel.infra.db.models import TaskStatus
from quantsentinel.services import task_service as task_module
from quantsentinel.services.task_service import TaskService


class FakeSession:
    pass


class FakeTasksRepo:
    def __init__(self, _session) -> None:
        self.task_id = uuid.uuid4()

    def create_task(self, *, task_type: str, actor_id):
        return self.task_id

    def list_recent(self, *, limit: int):
        return []


class FakeAuditRepo:
    def __init__(self, _session, sink: list[str]) -> None:
        self._sink = sink

    def write(self, entry):
        self._sink.append(entry.action)


def test_task_queue_writes_audit_and_enqueues(monkeypatch) -> None:
    audits: list[str] = []
    enqueued: list[dict] = []

    @contextmanager
    def fake_scope():
        yield FakeSession()

    monkeypatch.setattr(task_module, "session_scope", fake_scope)
    monkeypatch.setattr(task_module, "TasksRepo", FakeTasksRepo)
    monkeypatch.setattr(task_module, "AuditRepo", lambda session: FakeAuditRepo(session, audits))

    service = TaskService()
    monkeypatch.setattr(
        service,
        "_enqueue_celery",
        lambda signature, *, task_id, **kwargs: enqueued.append(
            {"signature": signature, "task_id": task_id, "kwargs": kwargs}
        ),
    )

    task_id = service.queue(
        task_type="ingest",
        actor_id=None,
        celery_signature="quantsentinel.infra.tasks.tasks_ingest.refresh_watchlist",
        celery_args={"force": True},
    )

    assert isinstance(task_id, uuid.UUID)
    assert "task_queued" in audits
    assert enqueued and enqueued[0]["kwargs"] == {"force": True}


def test_task_status_enum_expected_values() -> None:
    assert {item.value for item in TaskStatus} >= {"queued", "running", "success", "failed"}
