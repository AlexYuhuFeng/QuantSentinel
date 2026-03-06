"""
Notification service.

Scope (Team Edition):
- Provide a unified API for creating notifications from alert events
- Dispatch through channels: Email / Feishu / WeChat (enterprise) (no Slack)
- Persist notification records for auditability and UI "Notification Center"

Strict layering:
- Service orchestrates and chooses channels
- Providers implement channel specifics (infra/providers)
- Repos persist notifications (infra/db/repos)
"""

from __future__ import annotations

import uuid
from dataclasses import dataclass
from datetime import UTC, datetime
from typing import Any, Protocol

from quantsentinel.infra.db.engine import session_scope
from quantsentinel.infra.db.repos.audit_repo import AuditEntryCreate, AuditRepo
from quantsentinel.infra.db.repos.notifications_repo import NotificationCreate, NotificationsRepo


def _now() -> datetime:
    return datetime.now(UTC)


@dataclass(frozen=True)
class NotificationPayload:
    """
    Normalized notification payload.
    """
    title: str
    body: str
    severity: str = "MEDIUM"
    tags: list[str] | None = None
    context: dict[str, Any] | None = None


class NotificationChannel(Protocol):
    """
    Channel provider interface.
    """

    name: str

    def send(self, *, recipients: list[str], payload: NotificationPayload) -> None: ...


class NotificationService:
    """
    Orchestrates notification persistence + dispatch.

    Typical flow:
      - create_for_alert_event(...) -> create DB notification record (PENDING)
      - dispatch(notification_id) -> send via provider(s) -> mark SENT/FAILED
    """

    def __init__(
        self,
        *,
        email_channel: NotificationChannel | None = None,
        feishu_channel: NotificationChannel | None = None,
        wechat_channel: NotificationChannel | None = None,
    ) -> None:
        # Providers are optional at construction time; if None, dispatch will fail gracefully.
        self._email = email_channel
        self._feishu = feishu_channel
        self._wechat = wechat_channel

    # -----------------------------
    # Create
    # -----------------------------

    def create(
        self,
        *,
        actor_id: uuid.UUID | None,
        recipients: list[str],
        channels: list[str],
        payload: NotificationPayload,
        dedup_key: str | None = None,
        related_entity_type: str | None = None,
        related_entity_id: str | None = None,
    ) -> uuid.UUID:
        """
        Create a notification record (PENDING).

        recipients: list of strings. Channel provider interprets them (email addresses, user IDs, etc.).
        channels: subset of {"email","feishu","wechat"}.
        """
        now = _now()

        with session_scope() as session:
            repo = NotificationsRepo(session)
            audit = AuditRepo(session)

            notif_id = repo.create(
                NotificationCreate(
                    recipients=recipients,
                    channels=channels,
                    title=payload.title,
                    body=payload.body,
                    severity=payload.severity,
                    tags=payload.tags or [],
                    context=payload.context or {},
                    dedup_key=dedup_key,
                    related_entity_type=related_entity_type,
                    related_entity_id=related_entity_id,
                )
            )

            audit.write(
                AuditEntryCreate(
                    action="notification_created",
                    entity_type="notification",
                    entity_id=str(notif_id),
                    actor_id=actor_id,
                    payload={
                        "recipients": recipients,
                        "channels": channels,
                        "severity": payload.severity,
                        "dedup_key": dedup_key,
                        "related": {"type": related_entity_type, "id": related_entity_id},
                    },
                    ts=now,
                )
            )

            return notif_id

    # -----------------------------
    # Dispatch
    # -----------------------------

    def dispatch(self, *, notification_id: uuid.UUID) -> None:
        """
        Dispatch a pending notification using the configured providers.
        Updates DB status to SENT/FAILED with detail.
        """
        now = _now()

        with session_scope() as session:
            repo = NotificationsRepo(session)
            audit = AuditRepo(session)

            notif = repo.get(notification_id)
            if notif is None:
                raise ValueError("Notification not found.")

            if notif.status in {"SENT"}:
                return

            payload = NotificationPayload(
                title=notif.title,
                body=notif.body,
                severity=notif.severity,
                tags=list(notif.tags_json or []),
                context=dict(notif.context_json or {}),
            )

            failures: list[str] = []
            # Dispatch per channel
            for ch in notif.channels_json or []:
                try:
                    self._send_one(channel=ch, recipients=list(notif.recipients_json or []), payload=payload)
                except Exception as e:
                    failures.append(f"{ch}: {e}")

            if failures:
                repo.mark_failed(notification_id=notification_id, finished_at=now, detail="; ".join(failures))
                audit.write(
                    AuditEntryCreate(
                        action="notification_failed",
                        entity_type="notification",
                        entity_id=str(notification_id),
                        actor_id=None,
                        payload={"failures": failures},
                        ts=now,
                    )
                )
            else:
                repo.mark_sent(notification_id=notification_id, finished_at=now)
                audit.write(
                    AuditEntryCreate(
                        action="notification_sent",
                        entity_type="notification",
                        entity_id=str(notification_id),
                        actor_id=None,
                        payload={"channels": notif.channels_json, "recipients": notif.recipients_json},
                        ts=now,
                    )
                )

    def _send_one(self, *, channel: str, recipients: list[str], payload: NotificationPayload) -> None:
        channel = (channel or "").strip().lower()
        if channel == "email":
            if not self._email:
                raise RuntimeError("email channel not configured")
            self._email.send(recipients=recipients, payload=payload)
            return

        if channel == "feishu":
            if not self._feishu:
                raise RuntimeError("feishu channel not configured")
            self._feishu.send(recipients=recipients, payload=payload)
            return

        if channel == "wechat":
            if not self._wechat:
                raise RuntimeError("wechat channel not configured")
            self._wechat.send(recipients=recipients, payload=payload)
            return

        raise ValueError(f"Unknown channel: {channel}")