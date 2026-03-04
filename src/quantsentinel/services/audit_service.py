from __future__ import annotations

import uuid
from dataclasses import dataclass
from datetime import datetime
from typing import Any

from quantsentinel.infra.db.engine import session_scope
from quantsentinel.infra.db.repos.audit_repo import AuditEntryCreate, AuditRepo
from quantsentinel.services.rbac_service import AuditActionType


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
            normalized_payload = dict(payload or {})
            action_type = str(normalized_payload.get("action_type", AuditActionType.RUN.value)).lower()
            if action_type not in {item.value for item in AuditActionType}:
                action_type = AuditActionType.RUN.value
            normalized_payload["action_type"] = action_type
            normalized_payload.setdefault("command_id", command_id)
            normalized_payload.setdefault("actor_id", str(actor_id) if actor_id is not None else None)
            repo.write(
                AuditEntryCreate(
                    action="command_palette_execute",
                    entity_type="command_palette",
                    entity_id=command_id,
                    payload=normalized_payload,
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
