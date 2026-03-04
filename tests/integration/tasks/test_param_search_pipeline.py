from __future__ import annotations

from dataclasses import dataclass
from datetime import datetime
from types import SimpleNamespace
from uuid import UUID, uuid4

from quantsentinel.infra.db.models import TaskStatus
from quantsentinel.infra.tasks.tasks_research import run_param_search
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
        self.saved_runs: list[dict] = []


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
            return task_id

        def get(self, task_id: UUID):
            return store.tasks.get(task_id)

        def set_running(self, *, task_id: UUID, started_at: datetime):
            row = store.tasks[task_id]
            row.status = TaskStatus.RUNNING
            row.started_at = started_at
            row.updated_at = started_at

        def set_progress(self, *, task_id: UUID, progress: int, detail=None, log=None, append_log=False, updated_at=None):
            row = store.tasks[task_id]
            row.progress = progress
            if detail is not None:
                row.detail = detail
            if log is not None:
                row.log = f"{row.log}\n{log}" if append_log and row.log else log

        def set_success(self, *, task_id: UUID, finished_at: datetime, detail=None, log=None, append_log=False):
            row = store.tasks[task_id]
            row.status = TaskStatus.SUCCESS
            row.progress = 100
            row.finished_at = finished_at
            row.updated_at = finished_at
            if detail is not None:
                row.detail = detail
            if log is not None:
                row.log = f"{row.log}\n{log}" if append_log and row.log else log

        def set_failed(self, *, task_id: UUID, finished_at: datetime, detail=None, log=None, append_log=False):
            row = store.tasks[task_id]
            row.status = TaskStatus.FAILED
            row.finished_at = finished_at
            row.updated_at = finished_at
            if detail is not None:
                row.detail = detail
            if log is not None:
                row.log = f"{row.log}\n{log}" if append_log and row.log else log

    monkeypatch.setattr("quantsentinel.services.task_service.session_scope", lambda: FakeScope())
    monkeypatch.setattr("quantsentinel.services.task_service.TasksRepo", FakeTasksRepo)
    monkeypatch.setattr("quantsentinel.services.task_service.AuditRepo", lambda _session: SimpleNamespace(write=lambda _entry: None))
    monkeypatch.setattr("quantsentinel.services.task_service.TaskService._enqueue_celery", lambda *_args, **_kwargs: None)


def test_run_param_search_pipeline_persists_runs(monkeypatch) -> None:
    store = _Store()
    _patch_task_db(monkeypatch, store)

    class FakeScope:
        def __enter__(self):
            return object()

        def __exit__(self, exc_type, exc, tb):
            return False

    class FakeRunsRepo:
        def __init__(self, session) -> None:
            self._session = session

        def create_strategy_run(self, **kwargs):
            store.saved_runs.append(kwargs)
            return SimpleNamespace(**kwargs)

    monkeypatch.setattr("quantsentinel.infra.tasks.tasks_research.session_scope", lambda: FakeScope())
    monkeypatch.setattr("quantsentinel.infra.tasks.tasks_research.RunsRepo", FakeRunsRepo)

    svc = TaskService()
    task_id = svc.queue(task_type="run_param_search", actor_id=None, celery_signature=None)

    run_param_search.run(
        task_id=str(task_id),
        ticker="AAPL",
        start_date="2024-01-01",
        end_date="2024-12-31",
        family="ma_crossover",
        grid_size=6,
        sampler="random",
        seed=11,
    )

    row = store.tasks[task_id]
    assert row.status == TaskStatus.SUCCESS
    assert row.progress == 100
    assert row.detail is not None and "parameter search completed" in row.detail
    assert len(store.saved_runs) > 0
    assert "risk_adjusted_score" in store.saved_runs[0]["metrics_json"]
    assert "robustness_penalty" in store.saved_runs[0]["metrics_json"]
