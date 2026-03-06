"""Layout service."""

from __future__ import annotations

import uuid
from dataclasses import dataclass
from datetime import UTC, datetime
from typing import Any

from quantsentinel.infra.db.engine import session_scope
from quantsentinel.infra.db.models import LayoutWorkspace, UILayoutPreset, UserRole
from quantsentinel.infra.db.repos.audit_repo import AuditEntryCreate, AuditRepo
from quantsentinel.infra.db.repos.layouts_repo import LayoutPresetCreate, LayoutsRepo

LAYOUT_VERSION = 2


@dataclass(frozen=True)
class LayoutActionResult:
    layout_id: uuid.UUID
    name: str
    workspace: LayoutWorkspace
    layout_json: dict[str, Any]
    version: int
    is_default: bool


def migrate_layout(layout_json: dict[str, Any] | None) -> dict[str, Any]:
    """Migrate arbitrary historic layout payloads to current normalized schema."""
    source = dict(layout_json or {})
    panels = source.get("panels")
    if panels is None:
        panels = source.get("widgets", [])

    migrated = {
        "version": int(source.get("version") or source.get("schema_version") or LAYOUT_VERSION),
        "panels": panels if isinstance(panels, list) else [],
        "filters": source.get("filters") if isinstance(source.get("filters"), dict) else {},
        "meta": source.get("meta") if isinstance(source.get("meta"), dict) else {},
    }
    # normalize renamed key from v1 -> v2
    if "layoutName" in source and "name" not in migrated["meta"]:
        migrated["meta"]["name"] = source["layoutName"]

    migrated["version"] = LAYOUT_VERSION
    return migrated


class LayoutService:
    @staticmethod
    def can_manage_layouts(role: UserRole | None) -> bool:
        return role in (UserRole.ADMIN, UserRole.EDITOR)

    def save(
        self,
        *,
        actor_id: uuid.UUID,
        workspace: LayoutWorkspace,
        name: str,
        layout_json: dict[str, Any],
    ) -> LayoutActionResult:
        now = datetime.now(UTC)
        normalized = migrate_layout(layout_json)
        with session_scope() as session:
            repo = LayoutsRepo(session)
            audit = AuditRepo(session)
            existing = repo.get_by_name(user_id=actor_id, workspace=workspace, name=name)
            if existing is None:
                created = repo.create(
                    LayoutPresetCreate(
                        user_id=actor_id,
                        workspace=workspace,
                        name=name,
                        layout_json=normalized,
                        version=LAYOUT_VERSION,
                        is_default=False,
                    )
                )
                target = created
            else:
                repo.update_layout(
                    layout_id=existing.id,
                    name=None,
                    layout_json=normalized,
                    version=LAYOUT_VERSION,
                )
                session.flush()
                target = repo.get(existing.id)
                assert target is not None

            audit.write(
                AuditEntryCreate(
                    action="layout_save",
                    entity_type="ui_layout",
                    entity_id=str(target.id),
                    actor_id=actor_id,
                    payload={"workspace": workspace.value, "name": name, "version": LAYOUT_VERSION},
                    ts=now,
                )
            )
            return self._to_result(target)

    def save_as(
        self,
        *,
        actor_id: uuid.UUID,
        workspace: LayoutWorkspace,
        source_layout_id: uuid.UUID | None,
        new_name: str,
        layout_json: dict[str, Any] | None,
    ) -> LayoutActionResult:
        now = datetime.now(UTC)
        with session_scope() as session:
            repo = LayoutsRepo(session)
            audit = AuditRepo(session)
            if repo.get_by_name(user_id=actor_id, workspace=workspace, name=new_name) is not None:
                raise ValueError("Layout name already exists.")

            if source_layout_id is not None:
                source = repo.get(source_layout_id)
                if source is None or source.user_id != actor_id or source.workspace != workspace:
                    raise ValueError("Source layout not found.")
                content = source.layout_json
            else:
                content = layout_json or {}

            normalized = migrate_layout(content)
            created = repo.create(
                LayoutPresetCreate(
                    user_id=actor_id,
                    workspace=workspace,
                    name=new_name,
                    layout_json=normalized,
                    version=LAYOUT_VERSION,
                    is_default=False,
                )
            )
            audit.write(
                AuditEntryCreate(
                    action="layout_save_as",
                    entity_type="ui_layout",
                    entity_id=str(created.id),
                    actor_id=actor_id,
                    payload={"workspace": workspace.value, "name": new_name, "version": LAYOUT_VERSION},
                    ts=now,
                )
            )
            return self._to_result(created)

    def set_default(self, *, actor_id: uuid.UUID, workspace: LayoutWorkspace, layout_id: uuid.UUID) -> None:
        now = datetime.now(UTC)
        with session_scope() as session:
            repo = LayoutsRepo(session)
            audit = AuditRepo(session)

            target = repo.get(layout_id)
            if target is None or target.user_id != actor_id or target.workspace != workspace:
                raise ValueError("Layout not found.")

            repo.set_default(user_id=actor_id, workspace=workspace, layout_id=layout_id)
            audit.write(
                AuditEntryCreate(
                    action="layout_set_default",
                    entity_type="ui_layout",
                    entity_id=str(layout_id),
                    actor_id=actor_id,
                    payload={"workspace": workspace.value, "name": target.name},
                    ts=now,
                )
            )

    def delete(self, *, actor_id: uuid.UUID, workspace: LayoutWorkspace, layout_id: uuid.UUID) -> None:
        now = datetime.now(UTC)
        with session_scope() as session:
            repo = LayoutsRepo(session)
            audit = AuditRepo(session)
            target = repo.get(layout_id)
            if target is None or target.user_id != actor_id or target.workspace != workspace:
                raise ValueError("Layout not found.")
            was_default = target.is_default
            repo.delete(layout_id=layout_id, user_id=actor_id)

            if was_default:
                # fallback: set newest layout as default (if any remain)
                remaining = repo.list_for_workspace(user_id=actor_id, workspace=workspace)
                if remaining:
                    repo.set_default(user_id=actor_id, workspace=workspace, layout_id=remaining[0].id)

            audit.write(
                AuditEntryCreate(
                    action="layout_delete",
                    entity_type="ui_layout",
                    entity_id=str(layout_id),
                    actor_id=actor_id,
                    payload={"workspace": workspace.value, "name": target.name},
                    ts=now,
                )
            )

    def reset_to_default(self, *, actor_id: uuid.UUID, workspace: LayoutWorkspace) -> dict[str, Any]:
        now = datetime.now(UTC)
        with session_scope() as session:
            repo = LayoutsRepo(session)
            audit = AuditRepo(session)
            default_layout = repo.get_default(user_id=actor_id, workspace=workspace)
            if default_layout is None:
                normalized = migrate_layout({})
            else:
                normalized = migrate_layout(default_layout.layout_json)

            audit.write(
                AuditEntryCreate(
                    action="layout_reset",
                    entity_type="ui_layout",
                    entity_id=str(default_layout.id) if default_layout else None,
                    actor_id=actor_id,
                    payload={"workspace": workspace.value},
                    ts=now,
                )
            )
            return normalized

    def load_layouts(self, *, actor_id: uuid.UUID, workspace: LayoutWorkspace) -> list[LayoutActionResult]:
        with session_scope() as session:
            repo = LayoutsRepo(session)
            items = repo.list_for_workspace(user_id=actor_id, workspace=workspace)
            return [self._to_result(item) for item in items]

    @staticmethod
    def _to_result(layout: UILayoutPreset) -> LayoutActionResult:
        normalized = migrate_layout(layout.layout_json)
        return LayoutActionResult(
            layout_id=layout.id,
            name=layout.name,
            workspace=layout.workspace,
            layout_json=normalized,
            version=LAYOUT_VERSION,
            is_default=layout.is_default,
        )
