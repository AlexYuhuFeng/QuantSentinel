"""Layouts repository."""

from __future__ import annotations

import uuid
from dataclasses import dataclass
from typing import Any

from sqlalchemy import select, update
from sqlalchemy.orm import Session

from quantsentinel.infra.db.models import LayoutWorkspace, UILayoutPreset


@dataclass(frozen=True)
class LayoutPresetCreate:
    user_id: uuid.UUID
    workspace: LayoutWorkspace
    name: str
    layout_json: dict[str, Any]
    version: int
    is_default: bool = False


class LayoutsRepo:
    def __init__(self, session: Session) -> None:
        self._session = session

    def get(self, layout_id: uuid.UUID) -> UILayoutPreset | None:
        return self._session.get(UILayoutPreset, layout_id)

    def list_for_workspace(self, *, user_id: uuid.UUID, workspace: LayoutWorkspace) -> list[UILayoutPreset]:
        stmt = (
            select(UILayoutPreset)
            .where(UILayoutPreset.user_id == user_id, UILayoutPreset.workspace == workspace)
            .order_by(UILayoutPreset.updated_at.desc())
        )
        return list(self._session.execute(stmt).scalars().all())

    def get_by_name(self, *, user_id: uuid.UUID, workspace: LayoutWorkspace, name: str) -> UILayoutPreset | None:
        stmt = select(UILayoutPreset).where(
            UILayoutPreset.user_id == user_id,
            UILayoutPreset.workspace == workspace,
            UILayoutPreset.name == name,
        )
        return self._session.execute(stmt).scalar_one_or_none()

    def get_default(self, *, user_id: uuid.UUID, workspace: LayoutWorkspace) -> UILayoutPreset | None:
        stmt = select(UILayoutPreset).where(
            UILayoutPreset.user_id == user_id,
            UILayoutPreset.workspace == workspace,
            UILayoutPreset.is_default.is_(True),
        )
        return self._session.execute(stmt).scalar_one_or_none()

    def create(self, data: LayoutPresetCreate) -> UILayoutPreset:
        preset = UILayoutPreset(
            id=uuid.uuid4(),
            user_id=data.user_id,
            workspace=data.workspace,
            name=data.name,
            layout_json=data.layout_json,
            version=data.version,
            is_default=data.is_default,
        )
        self._session.add(preset)
        self._session.flush()
        return preset

    def update_layout(self, *, layout_id: uuid.UUID, name: str | None, layout_json: dict[str, Any], version: int) -> None:
        values: dict[str, Any] = {"layout_json": layout_json, "version": version}
        if name is not None:
            values["name"] = name
        stmt = update(UILayoutPreset).where(UILayoutPreset.id == layout_id).values(**values)
        self._session.execute(stmt)

    def clear_default_for_workspace(self, *, user_id: uuid.UUID, workspace: LayoutWorkspace) -> None:
        stmt = (
            update(UILayoutPreset)
            .where(UILayoutPreset.user_id == user_id, UILayoutPreset.workspace == workspace)
            .values(is_default=False)
        )
        self._session.execute(stmt)

    def set_default(self, *, user_id: uuid.UUID, workspace: LayoutWorkspace, layout_id: uuid.UUID) -> None:
        # Always guarantee workspace-wide uniqueness for default.
        self.clear_default_for_workspace(user_id=user_id, workspace=workspace)
        stmt = (
            update(UILayoutPreset)
            .where(
                UILayoutPreset.id == layout_id,
                UILayoutPreset.user_id == user_id,
                UILayoutPreset.workspace == workspace,
            )
            .values(is_default=True)
        )
        self._session.execute(stmt)

    def delete(self, *, layout_id: uuid.UUID, user_id: uuid.UUID) -> None:
        preset = self.get(layout_id)
        if preset is not None and preset.user_id == user_id:
            self._session.delete(preset)
            self._session.flush()
