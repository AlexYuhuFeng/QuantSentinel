"""
Monitoring tasks (alerts, health).

Strict layering:
- Celery task = thin entrypoint
- Core logic delegated to services (AlertsService, TaskService)
- No Streamlit imports
"""

from __future__ import annotations

import uuid
from datetime import datetime, timezone

from celery import shared_task

from quantsentinel.services.task_service import TaskService


def _utc_now() -> datetime:
    return datetime.now(timezone.utc)


def _as_uuid(task_id: str | None) -> uuid.UUID | None:
    if not task_id:
        return None
    try:
        return uuid.UUID(task_id)
    except Exception:
        return None


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
    task_uuid = _as_uuid(task_id)
    task_svc = TaskService()

    if task_uuid:
        task_svc.mark_running(task_id=task_uuid)
        task_svc.set_progress(task_id=task_uuid, progress=1, detail="starting monitor cycle")

    try:
        # Import lazily to avoid cycles during worker startup.
        from quantsentinel.services.alerts_service import AlertsService

        alerts = AlertsService()

        # One monitoring cycle:
        # - loads enabled rules
        # - evaluates rules against latest data
        # - applies governance (dedup/silence windows)
        # - writes alert_events
        # - triggers notifications (if enabled)
        result = alerts.run_monitor_cycle(
            actor_id=None,
            task_id=task_uuid,
        )

        # result contract:
        # {
        #   "rules_evaluated": int,
        #   "events_created": int,
        #   "events_deduped": int,
        #   "events_silenced": int,
        #   "detail": str|None
        # }
        detail = (
            f"rules={result.get('rules_evaluated', 0)}, "
            f"created={result.get('events_created', 0)}, "
            f"deduped={result.get('events_deduped', 0)}, "
            f"silenced={result.get('events_silenced', 0)}"
        )

        if task_uuid:
            task_svc.set_progress(task_id=task_uuid, progress=95, detail=detail)
            task_svc.mark_success(task_id=task_uuid, detail=detail)

    except Exception as e:
        if task_uuid:
            task_svc.mark_failed(task_id=task_uuid, detail=str(e))
        # For beat-run, we still want the exception visible to worker logs.
        raise