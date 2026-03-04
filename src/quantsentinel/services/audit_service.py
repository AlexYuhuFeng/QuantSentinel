from __future__ import annotations

import uuid
from dataclasses import dataclass
from datetime import datetime
from typing import Any

from quantsentinel.infra.db.engine import session_scope
from quantsentinel.infra.db.repos.audit_repo import AuditEntryCreate, AuditRepo


@dataclass(frozen=True)
class AuditLogView:
    ts: datetime
    actor_username: str | None
    action: str
    entity_type: str
    entity_id: str | None
    payload_json: dict[str, Any]


class AuditService:
    def log_command_palette_execution(
        self,
        *,
        actor_id: uuid.UUID | None,
        command_id: str,
        payload: dict[str, Any] | None = None,
    ) -> None:
        with session_scope() as session:
            repo = AuditRepo(session)
            repo.write(
                AuditEntryCreate(
                    action="command_palette_execute",
                    entity_type="command_palette",
                    entity_id=command_id,
                    payload={
                        "command_id": command_id,
                        "actor_id": str(actor_id) if actor_id is not None else None,
                        **(payload or {}),
                    },
                    actor_id=actor_id,
                )
            )

    def get_recent(self, *, limit: int = 200) -> list[AuditLogView]:
        with session_scope() as session:
            rows = AuditRepo(session).list_recent(limit=limit)
            return [
                AuditLogView(
                    ts=row.ts,
                    actor_username=row.actor.username if row.actor else None,
                    action=row.action,
                    entity_type=row.entity_type,
                    entity_id=row.entity_id,
                    payload_json=row.payload_json,
                )
                for row in rows
            ]
