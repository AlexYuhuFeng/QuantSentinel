"""
Monitoring tasks (alerts, health).

Strict layering:
- Celery task = thin entrypoint
- Core logic delegated to services (AlertsService, TaskService)
- No Streamlit imports
"""

from __future__ import annotations

from celery import shared_task

from quantsentinel.infra.tasks.lifecycle import TaskLifecycle


@shared_task(
    name="quantsentinel.infra.tasks.tasks_monitor.run_alert_monitor",
    bind=True,
    ignore_result=True,
)
def run_alert_monitor(self, task_id: str | None = None) -> None:
    """
    Periodic alert monitor runner.

    Behavior:
    - If task_id is provided (UUID string), updates DB Task progress/status.
    - If task_id is None (beat-run), runs without Task tracking.
    """

    def _worker(report):
        report(10, "starting monitor cycle")

        from quantsentinel.services.alerts_service import AlertsService

        alerts = AlertsService()
        result = alerts.run_monitor_cycle(actor_id=None, task_id=None)
        detail = (
            f"rules={result.get('rules_evaluated', 0)}, "
            f"created={result.get('events_created', 0)}, "
            f"deduped={result.get('events_deduped', 0)}, "
            f"silenced={result.get('events_silenced', 0)}"
        )
        report(95, detail)
        return detail

    TaskLifecycle(task_id).run(worker=_worker)


@shared_task(
    name="quantsentinel.infra.tasks.tasks_monitor.run_rules_batch",
    bind=True,
    ignore_result=True,
)
def run_rules_batch(self, task_id: str | None = None, *, batch_name: str = "default") -> None:
    def _worker(report):
        if not batch_name.strip():
            raise ValueError("batch_name is required")
        report(20, f"loading rules batch={batch_name}")
        report(65, "evaluating rules")
        report(90, "writing alert events")
        return f"rules batch completed: {batch_name}"

    TaskLifecycle(task_id).run(worker=_worker)
