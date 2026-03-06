from __future__ import annotations

import uuid
from dataclasses import dataclass
from datetime import UTC, datetime, timedelta
from typing import Any

from sqlalchemy import delete, select, update
from sqlalchemy.orm import Session

from quantsentinel.infra.db.models import AlertEvent, AlertEventStatus, AlertRule


def _utc_now() -> datetime:
    return datetime.now(UTC)


@dataclass(frozen=True)
class AlertRuleCreate:
    name: str
    rule_type: str
    scope_json: dict[str, Any] | None = None
    params_json: dict[str, Any] | None = None
    enabled: bool = True
    severity: str = "MEDIUM"
    dedup_key: str | None = None
    silenced_until: datetime | None = None
    created_by: uuid.UUID | None = None


@dataclass(frozen=True)
class AlertRuleUpdate:
    name: str | None = None
    rule_type: str | None = None
    scope_json: dict[str, Any] | None = None
    params_json: dict[str, Any] | None = None
    enabled: bool | None = None
    severity: str | None = None
    dedup_key: str | None = None
    silenced_until: datetime | None = None


@dataclass(frozen=True)
class AlertEventCreate:
    rule_id: uuid.UUID
    ticker: str
    message: str
    context: dict[str, Any]
    asof_date: Any | None
    status: AlertEventStatus = AlertEventStatus.NEW
    ack_by: uuid.UUID | None = None


class AlertsRepo:
    def __init__(self, session: Session) -> None:
        self._session = session

    def list_rules(self) -> list[AlertRule]:
        stmt = select(AlertRule).order_by(AlertRule.created_at.desc())
        return list(self._session.execute(stmt).scalars().all())

    def list_enabled_rules(self) -> list[AlertRule]:
        stmt = select(AlertRule).where(AlertRule.enabled.is_(True)).order_by(AlertRule.created_at.desc())
        return list(self._session.execute(stmt).scalars().all())

    def get_rule(self, rule_id: uuid.UUID) -> AlertRule | None:
        return self._session.get(AlertRule, rule_id)

    def create_rule(self, payload: AlertRuleCreate) -> uuid.UUID:
        rule = AlertRule(
            id=uuid.uuid4(),
            name=payload.name,
            rule_type=payload.rule_type,
            scope_json=payload.scope_json or {},
            params_json=payload.params_json or {},
            enabled=payload.enabled,
            severity=payload.severity,
            dedup_key=payload.dedup_key,
            silenced_until=payload.silenced_until,
            created_by=payload.created_by,
        )
        self._session.add(rule)
        self._session.flush()
        return rule.id

    def update_rule(self, *, rule_id: uuid.UUID, payload: AlertRuleUpdate) -> None:
        values: dict[str, Any] = {}
        for field in ("name", "rule_type", "scope_json", "params_json", "enabled", "severity", "dedup_key", "silenced_until"):
            val = getattr(payload, field)
            if val is not None:
                values[field] = val
        if not values:
            return
        stmt = update(AlertRule).where(AlertRule.id == rule_id).values(**values)
        self._session.execute(stmt)

    def set_rule_enabled(self, *, rule_id: uuid.UUID, enabled: bool) -> None:
        self._session.execute(update(AlertRule).where(AlertRule.id == rule_id).values(enabled=enabled))

    def set_rule_silenced_until(self, *, rule_id: uuid.UUID, silenced_until: datetime | None) -> None:
        self._session.execute(update(AlertRule).where(AlertRule.id == rule_id).values(silenced_until=silenced_until))

    def delete_rule(self, *, rule_id: uuid.UUID) -> int:
        res = self._session.execute(delete(AlertRule).where(AlertRule.id == rule_id))
        return int(res.rowcount or 0)


class EventsRepo:
    def __init__(self, session: Session) -> None:
        self._session = session

    def exists_recent(self, *, rule_id: uuid.UUID, ticker: str, window_minutes: int, aggregation_key: str | None = None) -> bool:
        if window_minutes <= 0:
            window_minutes = 60
        since = _utc_now() - timedelta(minutes=window_minutes)
        stmt = select(AlertEvent.id).where(AlertEvent.rule_id == rule_id, AlertEvent.event_ts >= since)
        if aggregation_key:
            stmt = stmt.where(AlertEvent.ticker == aggregation_key)
        else:
            stmt = stmt.where(AlertEvent.ticker == ticker)
        return self._session.execute(stmt.limit(1)).scalar_one_or_none() is not None

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

    def get(self, event_id: uuid.UUID) -> AlertEvent | None:
        return self._session.get(AlertEvent, event_id)

    def list_recent(self, *, limit: int = 200, status: AlertEventStatus | None = None) -> list[AlertEvent]:
        stmt = select(AlertEvent).order_by(AlertEvent.event_ts.desc()).limit(limit)
        if status is not None:
            stmt = stmt.where(AlertEvent.status == status)
        return list(self._session.execute(stmt).scalars().all())

    def ack(self, *, event_id: uuid.UUID, actor_id: uuid.UUID) -> None:
        now = _utc_now()
        self._session.execute(
            update(AlertEvent).where(AlertEvent.id == event_id).values(status=AlertEventStatus.ACKED, ack_ts=now, ack_by=actor_id)
        )
