"""
Task service (queueing + querying + status updates).

Strict layering:
- Service orchestrates (repos + optional celery)
- Repo persists state
- Celery tasks update progress via this service or repos
"""

from __future__ import annotations

import uuid
from dataclasses import dataclass
from datetime import datetime, timezone
from typing import Any

from quantsentinel.infra.db.engine import session_scope
from quantsentinel.infra.db.models import TaskStatus
from quantsentinel.infra.db.repos.audit_repo import AuditEntryCreate, AuditRepo
from quantsentinel.infra.db.repos.tasks_repo import TasksRepo


def _now() -> datetime:
    return datetime.now(timezone.utc)


@dataclass(frozen=True)
class TaskSummary:
    id: uuid.UUID
    task_type: str
    status: TaskStatus
    progress: int
    created_at: datetime
    updated_at: datetime
    detail: str | None
    started_at: datetime | None
    finished_at: datetime | None
    actor_id: uuid.UUID | None


class TaskService:
    # -----------------------------
    # Queue
    # -----------------------------

    def queue(
        self,
        *,
        task_type: str,
        actor_id: uuid.UUID | None,
        celery_signature: str | None = None,
        celery_args: dict[str, Any] | None = None,
    ) -> uuid.UUID:
        """
        Create a Task record and (best-effort) enqueue a Celery job.

        celery_signature: dotted path or symbolic name of a Celery task, e.g.
            "quantsentinel.infra.tasks.tasks_ingest.refresh_watchlist"
        celery_args: kwargs dict for celery task

        Returns:
            task_id (UUID)
        """
        celery_args = celery_args or {}
        now = _now()

        with session_scope() as session:
            tasks = TasksRepo(session)
            audit = AuditRepo(session)

            task_id = tasks.create_task(task_type=task_type, actor_id=actor_id)

            audit.write(
                AuditEntryCreate(
                    action="task_queued",
                    entity_type="task",
                    entity_id=str(task_id),
                    actor_id=actor_id,
                    payload={
                        "task_type": task_type,
                        "celery_signature": celery_signature,
                        "celery_args": celery_args,
                    },
                    ts=now,
                )
            )

        # Enqueue after commit boundary (best practice)
        if celery_signature:
            self._enqueue_celery(celery_signature, task_id=task_id, **celery_args)

        return task_id

    def _enqueue_celery(self, signature: str, *, task_id: uuid.UUID, **kwargs: Any) -> None:
        """
        Best-effort Celery enqueue. Must never crash caller.
        """
        try:
            # Import lazily to avoid import cycles during app startup.
            from celery import current_app  # type: ignore

            task_name = signature
            current_app.send_task(task_name, kwargs={"task_id": str(task_id), **kwargs})
        except Exception:
            # Celery not wired yet or worker not up; DB task still exists.
            pass

    # -----------------------------
    # Query
    # -----------------------------

    def list_recent(self, *, limit: int = 200) -> list[TaskSummary]:
        with session_scope() as session:
            tasks = TasksRepo(session)
            rows = tasks.list_recent(limit=limit)

            return [
                TaskSummary(
                    id=r.id,
                    task_type=r.task_type,
                    status=r.status,
                    progress=r.progress,
                    created_at=r.created_at,
                    updated_at=r.updated_at,
                    detail=r.detail,
                    started_at=r.started_at,
                    finished_at=r.finished_at,
                    actor_id=r.actor_id,
                )
                for r in rows
            ]

    def get(self, task_id: uuid.UUID) -> TaskSummary | None:
        with session_scope() as session:
            tasks = TasksRepo(session)
            r = tasks.get(task_id)
            if r is None:
                return None
            return TaskSummary(
                id=r.id,
                task_type=r.task_type,
                status=r.status,
                progress=r.progress,
                created_at=r.created_at,
                updated_at=r.updated_at,
                detail=r.detail,
                started_at=r.started_at,
                finished_at=r.finished_at,
                actor_id=r.actor_id,
            )

    # -----------------------------
    # Worker-side status updates
    # -----------------------------

    def mark_running(self, *, task_id: uuid.UUID) -> None:
        now = _now()
        with session_scope() as session:
            TasksRepo(session).set_running(task_id=task_id, started_at=now)

    def set_progress(self, *, task_id: uuid.UUID, progress: int, detail: str | None = None) -> None:
        with session_scope() as session:
            TasksRepo(session).set_progress(task_id=task_id, progress=progress, detail=detail)

    def mark_success(self, *, task_id: uuid.UUID, detail: str | None = None) -> None:
        now = _now()
        with session_scope() as session:
            TasksRepo(session).set_success(task_id=task_id, finished_at=now, detail=detail)

    def mark_failed(self, *, task_id: uuid.UUID, detail: str | None = None) -> None:
        now = _now()
        with session_scope() as session:
            TasksRepo(session).set_failed(task_id=task_id, finished_at=now, detail=detail)