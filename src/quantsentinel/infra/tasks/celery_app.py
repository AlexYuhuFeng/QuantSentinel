"""
Celery application factory for QuantSentinel.

Rules:
- Configuration must come from Settings (single source of truth).
- Importing this module must not start any tasks; only define celery_app.
- Beat schedule must be centrally defined (beat_schedule.py).
"""

from __future__ import annotations

from celery import Celery

from quantsentinel.common.config import get_settings
from quantsentinel.infra.tasks.beat_schedule import build_beat_schedule


def _make_celery() -> Celery:
    settings = get_settings()

    celery = Celery(
        "quantsentinel",
        broker=settings.celery_broker_url,
        backend=settings.celery_result_backend,
        include=[
            # Task modules to register
            "quantsentinel.infra.tasks.tasks_ingest",
            "quantsentinel.infra.tasks.tasks_monitor",
            "quantsentinel.infra.tasks.tasks_research",
            "quantsentinel.infra.tasks.tasks_snapshot",
        ],
    )

    # Sensible defaults for internal team usage.
    celery.conf.update(
        task_serializer="json",
        result_serializer="json",
        accept_content=["json"],
        timezone="UTC",
        enable_utc=True,
        task_track_started=True,
        worker_prefetch_multiplier=1,
        task_acks_late=True,
        broker_connection_retry_on_startup=True,
        beat_schedule=build_beat_schedule(),
    )

    return celery


celery_app: Celery = _make_celery()