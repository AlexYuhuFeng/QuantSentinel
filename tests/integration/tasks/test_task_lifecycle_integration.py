from __future__ import annotations

from dataclasses import dataclass
from datetime import datetime
from types import SimpleNamespace
from uuid import UUID, uuid4

from quantsentinel.infra.db.models import TaskStatus
from quantsentinel.infra.tasks.tasks_ingest import refresh_ticker
from quantsentinel.infra.tasks.tasks_monitor import run_rules_batch
from quantsentinel.services.task_service import TaskService


@dataclass
class _TaskRow:
    id: UUID
    task_type: str
    status: TaskStatus
    progress: int
    detail: str | None
    log: str | None
    started_at: datetime | None
    finished_at: datetime | None
    actor_id: UUID | None
    created_at: datetime
    updated_at: datetime


class _Store:
    def __init__(self) -> None:
        self.tasks: dict[UUID, _TaskRow] = {}
        self.transitions: list[tuple[UUID, str, TaskStatus, int]] = []


def _patch_task_db(monkeypatch, store: _Store) -> None:
    class FakeScope:
        def __enter__(self):
            return object()

        def __exit__(self, exc_type, exc, tb):
            return False

    class FakeTasksRepo:
        def __init__(self, session) -> None:
            self._session = session

        def create_task(self, *, task_type: str, actor_id=None):
            now = datetime.utcnow()
            task_id = uuid4()
            store.tasks[task_id] = _TaskRow(
                id=task_id,
                task_type=task_type,
                status=TaskStatus.PENDING,
                progress=0,
                detail=None,
                log=None,
                started_at=None,
                finished_at=None,
                actor_id=actor_id,
                created_at=now,
                updated_at=now,
            )
            store.transitions.append((task_id, "create", TaskStatus.PENDING, 0))
            return task_id

        def list_recent(self, *, limit: int = 200):
            rows = sorted(store.tasks.values(), key=lambda r: r.created_at, reverse=True)
            return rows[:limit]

        def get(self, task_id: UUID):
            return store.tasks.get(task_id)

        def set_running(self, *, task_id: UUID, started_at: datetime):
            row = store.tasks[task_id]
            row.status = TaskStatus.RUNNING
            row.started_at = started_at
            row.updated_at = started_at
            store.transitions.append((task_id, "running", row.status, row.progress))

        def set_progress(
            self,
            *,
            task_id: UUID,
            progress: int,
            detail: str | None = None,
            log: str | None = None,
            append_log: bool = False,
            updated_at=None,
        ):
            row = store.tasks[task_id]
            row.progress = progress
            if detail is not None:
                row.detail = detail
            if log is not None:
                row.log = f"{row.log}\n{log}" if append_log and row.log else log
            store.transitions.append((task_id, "progress", row.status, row.progress))

        def set_success(
            self,
            *,
            task_id: UUID,
            finished_at: datetime,
            detail: str | None = None,
            log: str | None = None,
            append_log: bool = False,
        ):
            row = store.tasks[task_id]
            row.status = TaskStatus.SUCCESS
            row.progress = 100
            row.finished_at = finished_at
            row.updated_at = finished_at
            if detail is not None:
                row.detail = detail
            if log is not None:
                row.log = f"{row.log}\n{log}" if append_log and row.log else log
            store.transitions.append((task_id, "success", row.status, row.progress))

        def set_failed(
            self,
            *,
            task_id: UUID,
            finished_at: datetime,
            detail: str | None = None,
            log: str | None = None,
            append_log: bool = False,
        ):
            row = store.tasks[task_id]
            row.status = TaskStatus.FAILED
            row.finished_at = finished_at
            row.updated_at = finished_at
            if detail is not None:
                row.detail = detail
            if log is not None:
                row.log = f"{row.log}\n{log}" if append_log and row.log else log
            store.transitions.append((task_id, "failed", row.status, row.progress))

    class FakeAuditRepo:
        def __init__(self, session) -> None:
            self._session = session

        def write(self, entry) -> None:
            return None

    monkeypatch.setattr("quantsentinel.services.task_service.session_scope", lambda: FakeScope())
    monkeypatch.setattr("quantsentinel.services.task_service.TasksRepo", FakeTasksRepo)
    monkeypatch.setattr("quantsentinel.services.task_service.AuditRepo", FakeAuditRepo)
    monkeypatch.setattr("quantsentinel.services.task_service.TaskService._enqueue_celery", lambda *args, **kwargs: None)


def test_enqueue_then_refresh_ticker_status_flow(monkeypatch) -> None:
    store = _Store()
    _patch_task_db(monkeypatch, store)

    monkeypatch.setattr("quantsentinel.infra.tasks.tasks_ingest._latest_price_date", lambda ticker: None)
    monkeypatch.setattr("quantsentinel.infra.tasks.tasks_ingest._today_utc_date", lambda: datetime(2024, 1, 10).date())
    monkeypatch.setattr(
        "quantsentinel.infra.tasks.tasks_ingest._provider_fetch_daily_prices",
        lambda **kwargs: [{"date": "2024-01-10", "close": 100.0}],
    )

    class FakeScope:
        def __enter__(self):
            return object()

        def __exit__(self, exc_type, exc, tb):
            return False

    monkeypatch.setattr("quantsentinel.infra.tasks.tasks_ingest.session_scope", lambda: FakeScope())
    monkeypatch.setattr("quantsentinel.infra.tasks.tasks_ingest.PricesRepo", lambda session: SimpleNamespace(upsert_many=lambda models: None))

    svc = TaskService()
    task_id = svc.queue(task_type="refresh_ticker", actor_id=None, celery_signature=None)
    assert store.tasks[task_id].status == TaskStatus.PENDING

    refresh_ticker.run(task_id=str(task_id), ticker="AAPL")

    row = store.tasks[task_id]
    assert row.status == TaskStatus.SUCCESS
    assert row.progress == 100
    assert row.started_at is not None
    assert row.finished_at is not None
    assert any(kind == "running" for _tid, kind, _status, _p in store.transitions)
    assert any(kind == "success" for _tid, kind, _status, _p in store.transitions)


def test_enqueue_then_rules_batch_status_flow(monkeypatch) -> None:
    store = _Store()
    _patch_task_db(monkeypatch, store)

    svc = TaskService()
    task_id = svc.queue(task_type="run_rules_batch", actor_id=None, celery_signature=None)

    run_rules_batch.run(task_id=str(task_id), batch_name="nightly")

    row = store.tasks[task_id]
    assert row.status == TaskStatus.SUCCESS
    assert row.detail == "rules batch completed: nightly"
    assert row.log is not None and "rules batch completed: nightly" in row.log
    assert row.progress == 100
    assert [item[1] for item in store.transitions if item[0] == task_id][:2] == ["create", "running"]


def test_rules_batch_failure_updates_failed_status(monkeypatch) -> None:
    store = _Store()
    _patch_task_db(monkeypatch, store)

    svc = TaskService()
    task_id = svc.queue(task_type="run_rules_batch", actor_id=None, celery_signature=None)

    try:
        run_rules_batch.run(task_id=str(task_id), batch_name="")
        assert False, "expected ValueError"
    except ValueError:
        pass

    row = store.tasks[task_id]
    assert row.status == TaskStatus.FAILED
    assert row.detail == "batch_name is required"
    assert row.log is not None and "batch_name is required" in row.log
