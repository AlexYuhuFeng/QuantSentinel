"""
Tasks repository.

Responsibilities:
- Create and update Task records (tracking background jobs)
- No Celery imports, no scheduling logic
"""

from __future__ import annotations

import uuid
from dataclasses import dataclass
from datetime import datetime, timezone

from sqlalchemy import select, update
from sqlalchemy.orm import Session

from quantsentinel.infra.db.models import Task, TaskStatus


@dataclass(frozen=True)
class TaskCreate:
    task_type: str
    actor_id: uuid.UUID | None = None


class TasksRepo:
    def __init__(self, session: Session) -> None:
        self._session = session

    def get(self, task_id: uuid.UUID) -> Task | None:
        return self._session.get(Task, task_id)

    def create_task(self, *, task_type: str, actor_id: uuid.UUID | None = None) -> uuid.UUID:
        task_id = uuid.uuid4()
        task = Task(
            id=task_id,
            task_type=task_type,
            status=TaskStatus.PENDING,
            progress=0,
            detail=None,
            log=None,
            started_at=None,
            finished_at=None,
            actor_id=actor_id,
        )
        self._session.add(task)
        self._session.flush()
        return task_id

    def list_recent(self, *, limit: int = 200) -> list[Task]:
        stmt = select(Task).order_by(Task.created_at.desc()).limit(limit)
        return list(self._session.execute(stmt).scalars().all())

    def set_running(self, *, task_id: uuid.UUID, started_at: datetime) -> None:
        stmt = (
            update(Task)
            .where(Task.id == task_id)
            .values(status=TaskStatus.RUNNING, started_at=started_at, updated_at=started_at)
        )
        self._session.execute(stmt)

    def set_progress(
        self,
        *,
        task_id: uuid.UUID,
        progress: int,
        detail: str | None = None,
        log: str | None = None,
        append_log: bool = False,
        updated_at: datetime | None = None,
    ) -> None:
        if progress < 0:
            progress = 0
        if progress > 100:
            progress = 100

        values = {"progress": progress}
        if updated_at is None:
            updated_at = datetime.now(timezone.utc)
        values["updated_at"] = updated_at
        if detail is not None:
            values["detail"] = detail
        if log is not None:
            if append_log:
                current = self.get(task_id)
                existing = current.log if current else None
                values["log"] = f"{existing}\n{log}" if existing else log
            else:
                values["log"] = log

        stmt = update(Task).where(Task.id == task_id).values(**values)
        self._session.execute(stmt)

    def set_success(
        self,
        *,
        task_id: uuid.UUID,
        finished_at: datetime,
        detail: str | None = None,
        log: str | None = None,
        append_log: bool = False,
    ) -> None:
        values = {
            "status": TaskStatus.SUCCESS,
            "progress": 100,
            "finished_at": finished_at,
            "updated_at": finished_at,
        }
        if detail is not None:
            values["detail"] = detail
        if log is not None:
            if append_log:
                current = self.get(task_id)
                existing = current.log if current else None
                values["log"] = f"{existing}\n{log}" if existing else log
            else:
                values["log"] = log

        stmt = update(Task).where(Task.id == task_id).values(**values)
        self._session.execute(stmt)

    def set_failed(
        self,
        *,
        task_id: uuid.UUID,
        finished_at: datetime,
        detail: str | None = None,
        log: str | None = None,
        append_log: bool = False,
    ) -> None:
        values = {
            "status": TaskStatus.FAILED,
            "finished_at": finished_at,
            "updated_at": finished_at,
        }
        if detail is not None:
            values["detail"] = detail
        if log is not None:
            if append_log:
                current = self.get(task_id)
                existing = current.log if current else None
                values["log"] = f"{existing}\n{log}" if existing else log
            else:
                values["log"] = log

        stmt = update(Task).where(Task.id == task_id).values(**values)
        self._session.execute(stmt)

    def cancel(self, *, task_id: uuid.UUID, finished_at: datetime, detail: str | None = None) -> None:
        values = {
            "status": TaskStatus.CANCELED,
            "finished_at": finished_at,
            "updated_at": finished_at,
        }
        if detail is not None:
            values["detail"] = detail

        stmt = update(Task).where(Task.id == task_id).values(**values)
        self._session.execute(stmt)
