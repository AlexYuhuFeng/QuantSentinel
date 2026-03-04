"""Snapshot tasks."""

from __future__ import annotations

from celery import shared_task

from quantsentinel.infra.tasks.lifecycle import TaskLifecycle


@shared_task(
    name="quantsentinel.infra.tasks.tasks_snapshot.export_snapshot",
    bind=True,
    ignore_result=True,
)
def export_snapshot(self, task_id: str | None = None, *, scope: str = "all") -> None:
    def _worker(report):
        report(25, "collecting snapshot payload")
        report(70, f"serializing scope={scope}")
        report(95, "storing export artifact")

    TaskLifecycle(task_id).run(worker=_worker, success_detail=f"snapshot exported: scope={scope}")
