from __future__ import annotations

import uuid
from collections.abc import Callable
from contextlib import suppress
from dataclasses import dataclass
from typing import TypeVar

from quantsentinel.services.task_service import TaskService

T = TypeVar("T")


@dataclass(frozen=True)
class TaskLifecycle:
    """Helper for consistent DB task lifecycle updates in worker tasks."""

    task_id: str | None

    def _as_uuid(self) -> uuid.UUID | None:
        if not self.task_id:
            return None
        with suppress(Exception):
            return uuid.UUID(self.task_id)
        return None

    def run(
        self,
        *,
        worker: Callable[[Callable[[int, str | None], None]], T],
        success_detail: str | None = None,
    ) -> T:
        svc = TaskService()
        task_uuid = self._as_uuid()

        def report(progress: int, detail: str | None = None) -> None:
            if task_uuid:
                svc.set_progress(task_id=task_uuid, progress=progress, detail=detail)

        if task_uuid:
            svc.mark_running(task_id=task_uuid)
            report(1, "started")

        try:
            result = worker(report)
            if task_uuid:
                final_detail = success_detail
                if final_detail is None and isinstance(result, str):
                    final_detail = result
                report(100, final_detail or "completed")
                svc.mark_success(task_id=task_uuid, detail=final_detail)
            return result
        except Exception as exc:
            if task_uuid:
                svc.mark_failed(task_id=task_uuid, detail=str(exc))
            raise
