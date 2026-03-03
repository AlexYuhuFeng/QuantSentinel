"""
Notifications repository.

Responsibilities:
- Persist Notification records
- Dedup helpers (by dedup_key)
- Status transitions: PENDING -> SENT/FAILED

Non-responsibilities:
- Channel/provider sending
- Rendering/UI
"""

from __future__ import annotations

import uuid
from dataclasses import dataclass
from datetime import datetime, timedelta, timezone
from typing import Any

from sqlalchemy import select, update
from sqlalchemy.orm import Session

from quantsentinel.infra.db.models import Notification


def _utc_now() -> datetime:
    return datetime.now(timezone.utc)


@dataclass(frozen=True)
class NotificationCreate:
    recipients: list[str]
    channels: list[str]  # subset of {"email","feishu","wechat"}
    title: str
    body: str
    severity: str = "MEDIUM"
    tags: list[str] | None = None
    context: dict[str, Any] | None = None
    dedup_key: str | None = None
    related_entity_type: str | None = None
    related_entity_id: str | None = None


class NotificationsRepo:
    def __init__(self, session: Session) -> None:
        self._session = session

    # -----------------------------
    # Read
    # -----------------------------

    def get(self, notification_id: uuid.UUID) -> Notification | None:
        return self._session.get(Notification, notification_id)

    def list_recent(self, *, limit: int = 200) -> list[Notification]:
        stmt = select(Notification).order_by(Notification.created_at.desc()).limit(limit)
        return list(self._session.execute(stmt).scalars().all())

    # -----------------------------
    # Dedup
    # -----------------------------

    def exists_recent_by_dedup_key(self, *, dedup_key: str, window_minutes: int = 60) -> bool:
        """
        Returns True if any notification with dedup_key was created within the time window.
        """
        if not dedup_key:
            return False
        if window_minutes <= 0:
            window_minutes = 60

        since = _utc_now() - timedelta(minutes=window_minutes)

        stmt = (
            select(Notification.id)
            .where(Notification.dedup_key == dedup_key, Notification.created_at >= since)
            .limit(1)
        )
        return self._session.execute(stmt).scalar_one_or_none() is not None

    # -----------------------------
    # Create
    # -----------------------------

    def create(self, data: NotificationCreate) -> uuid.UUID:
        notif_id = uuid.uuid4()

        notif = Notification(
            id=notif_id,
            status="PENDING",
            recipients_json=list(data.recipients or []),
            channels_json=[c.strip().lower() for c in (data.channels or []) if str(c).strip()],
            title=data.title,
            body=data.body,
            severity=data.severity,
            tags_json=list(data.tags or []),
            context_json=dict(data.context or {}),
            dedup_key=data.dedup_key,
            related_entity_type=data.related_entity_type,
            related_entity_id=data.related_entity_id,
            detail=None,
            finished_at=None,
        )
        self._session.add(notif)
        self._session.flush()
        return notif_id

    # -----------------------------
    # Status transitions
    # -----------------------------

    def mark_sent(self, *, notification_id: uuid.UUID, finished_at: datetime) -> None:
        stmt = (
            update(Notification)
            .where(Notification.id == notification_id)
            .values(status="SENT", finished_at=finished_at, updated_at=finished_at)
        )
        self._session.execute(stmt)

    def mark_failed(self, *, notification_id: uuid.UUID, finished_at: datetime, detail: str | None) -> None:
        stmt = (
            update(Notification)
            .where(Notification.id == notification_id)
            .values(status="FAILED", finished_at=finished_at, updated_at=finished_at, detail=detail)
        )
        self._session.execute(stmt)