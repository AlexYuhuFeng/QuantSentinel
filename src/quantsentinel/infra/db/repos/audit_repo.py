"""
Audit log repository.

Rules:
- Repo only persists audit entries (no RBAC decisions).
- Session injected; commit controlled by services layer.
"""

from __future__ import annotations

import uuid
from dataclasses import dataclass
from datetime import datetime
from typing import Any

from sqlalchemy import select
from sqlalchemy.orm import Session

from quantsentinel.infra.db.models import AuditLog


@dataclass(frozen=True)
class AuditEntryCreate:
    """
    Input DTO for writing an audit log entry.
    """
    action: str
    entity_type: str
    entity_id: str | None
    payload: dict[str, Any]
    actor_id: uuid.UUID | None = None
    ts: datetime | None = None


class AuditRepo:
    """Repository for AuditLog entries."""

    def __init__(self, session: Session) -> None:
        self._session = session

    def write(self, entry: AuditEntryCreate) -> AuditLog:
        log = AuditLog(
            actor_id=entry.actor_id,
            action=entry.action,
            entity_type=entry.entity_type,
            entity_id=entry.entity_id,
            payload_json=entry.payload,
        )
        if entry.ts is not None:
            log.ts = entry.ts
        self._session.add(log)
        self._session.flush()
        return log

    def list_recent(self, *, limit: int = 200) -> list[AuditLog]:
        stmt = select(AuditLog).order_by(AuditLog.ts.desc()).limit(limit)
        return list(self._session.execute(stmt).scalars().all())

    def list_by_actor(self, actor_id: uuid.UUID, *, limit: int = 200) -> list[AuditLog]:
        stmt = (
            select(AuditLog)
            .where(AuditLog.actor_id == actor_id)
            .order_by(AuditLog.ts.desc())
            .limit(limit)
        )
        return list(self._session.execute(stmt).scalars().all())

    def list_by_entity(
        self, entity_type: str, entity_id: str, *, limit: int = 200
    ) -> list[AuditLog]:
        stmt = (
            select(AuditLog)
            .where(AuditLog.entity_type == entity_type, AuditLog.entity_id == entity_id)
            .order_by(AuditLog.ts.desc())
            .limit(limit)
        )
        return list(self._session.execute(stmt).scalars().all())