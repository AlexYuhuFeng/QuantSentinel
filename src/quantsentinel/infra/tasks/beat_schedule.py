"""
Celery Beat schedule definitions.

Rules:
- Only define periodic schedules here.
- Do NOT import Streamlit.
- Keep side effects minimal.
"""

from __future__ import annotations

from datetime import timedelta


def build_beat_schedule() -> dict:
    """
    Returns Celery beat_schedule dict.
    """
    return {
        # Refresh watched instruments daily (placeholder cadence)
        "refresh_watchlist_daily": {
            "task": "quantsentinel.infra.tasks.tasks_ingest.refresh_watchlist",
            "schedule": timedelta(hours=24),
            "kwargs": {"task_id": None},  # beat-run has no UI Task id
        },
        # Monitor alerts every 5 minutes
        "monitor_alerts_5m": {
            "task": "quantsentinel.infra.tasks.tasks_monitor.run_alert_monitor",
            "schedule": timedelta(minutes=5),
            "kwargs": {"task_id": None},
        },
    }