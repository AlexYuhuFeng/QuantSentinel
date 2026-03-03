"""
Alert events repository.

Responsibilities:
- Persist and query AlertEvent
- Governance helpers (exists_recent for dedup)
- Ack operations

Non-responsibilities:
- Rule evaluation (domain/service)
- Notification sending
"""

from __future__ import annotations

import uuid
from dataclasses import dataclass
from datetime import datetime, timedelta, timezone
from typing import Any

from sqlalchemy import and_, select, update
from sqlalchemy.orm import Session

from quantsentinel.infra.db.models import AlertEvent, AlertEventStatus


def _utc_now() -> datetime:
    return datetime.now(timezone.utc)


@dataclass(frozen=True)
class AlertEventCreate:
    rule_id: uuid.UUID
    ticker: str
    message: str
    context: dict[str, Any]
    asof_date: Any | None  # date preferred; keep Any to avoid importing date here
    status: AlertEventStatus = AlertEventStatus.NEW
    ack_by: uuid.UUID | None = None


class EventsRepo:
    def __init__(self, session: Session) -> None:
        self._session = session

    # -----------------------------
    # Dedup / governance
    # -----------------------------

    def exists_recent(self, *, rule_id: uuid.UUID, ticker: str, window_minutes: int) -> bool:
        """
        Returns True if an event exists for (rule_id, ticker) within the time window.
        """
        if window_minutes <= 0:
            window_minutes = 60

        since = _utc_now() - timedelta(minutes=window_minutes)

        stmt = (
            select(AlertEvent.id)
            .where(
                AlertEvent.rule_id == rule_id,
                AlertEvent.ticker == ticker,
                AlertEvent.event_ts >= since,
            )
            .limit(1)
        )
        return self._session.execute(stmt).scalar_one_or_none() is not None

    # -----------------------------
    # Create
    # -----------------------------

    def create_event(
        self,
        *,
        rule_id: uuid.UUID,
        ticker: str,
        message: str,
        context: dict[str, Any] | None,
        asof_date: Any | None,
        status: AlertEventStatus,
        ack_by: uuid.UUID | None,
    ) -> uuid.UUID:
        event_id = uuid.uuid4()
        ev = AlertEvent(
            id=event_id,
            rule_id=rule_id,
            ticker=ticker,
            event_ts=_utc_now(),
            asof_date=asof_date,
            message=message,
            context_json=context or {},
            status=status,
            ack_ts=_utc_now() if status == AlertEventStatus.ACKED else None,
            ack_by=ack_by,
        )
        self._session.add(ev)
        self._session.flush()
        return event_id

    # -----------------------------
    # Read
    # -----------------------------

    def get(self, event_id: uuid.UUID) -> AlertEvent | None:
        return self._session.get(AlertEvent, event_id)

    def list_recent(self, *, limit: int = 200, status: AlertEventStatus | None = None) -> list[AlertEvent]:
        stmt = select(AlertEvent).order_by(AlertEvent.event_ts.desc()).limit(limit)
        if status is not None:
            stmt = stmt.where(AlertEvent.status == status)
        return list(self._session.execute(stmt).scalars().all())

    def list_by_rule(self, *, rule_id: uuid.UUID, limit: int = 200) -> list[AlertEvent]:
        stmt = (
            select(AlertEvent)
            .where(AlertEvent.rule_id == rule_id)
            .order_by(AlertEvent.event_ts.desc())
            .limit(limit)
        )
        return list(self._session.execute(stmt).scalars().all())

    def list_by_ticker(self, *, ticker: str, limit: int = 200) -> list[AlertEvent]:
        stmt = (
            select(AlertEvent)
            .where(AlertEvent.ticker == ticker)
            .order_by(AlertEvent.event_ts.desc())
            .limit(limit)
        )
        return list(self._session.execute(stmt).scalars().all())

    # -----------------------------
    # Ack / state transitions
    # -----------------------------

    def ack(self, *, event_id: uuid.UUID, actor_id: uuid.UUID) -> None:
        now = _utc_now()
        stmt = (
            update(AlertEvent)
            .where(AlertEvent.id == event_id)
            .values(status=AlertEventStatus.ACKED, ack_ts=now, ack_by=actor_id)
        )
        self._session.execute(stmt)

    def unack(self, *, event_id: uuid.UUID) -> None:
        stmt = (
            update(AlertEvent)
            .where(AlertEvent.id == event_id)
            .values(status=AlertEventStatus.NEW, ack_ts=None, ack_by=None)
        )
        self._session.execute(stmt)