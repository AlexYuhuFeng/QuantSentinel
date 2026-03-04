from __future__ import annotations

import uuid
from contextlib import contextmanager
from dataclasses import dataclass, field
from datetime import UTC, datetime

import pytest

from quantsentinel.infra.db.models import LayoutWorkspace
from quantsentinel.services import layout_service as layout_module
from quantsentinel.services.layout_service import LAYOUT_VERSION, LayoutService, migrate_layout


@dataclass
class FakeLayout:
    id: uuid.UUID
    user_id: uuid.UUID
    workspace: LayoutWorkspace
    name: str
    layout_json: dict
    version: int
    is_default: bool = False
    updated_at: datetime = field(default_factory=lambda: datetime.now(UTC))


class FakeSession:
    def flush(self) -> None:
        return


class FakeLayoutsRepo:
    def __init__(self, _session, store: dict[uuid.UUID, FakeLayout]) -> None:
        self._store = store

    def get(self, layout_id: uuid.UUID):
        return self._store.get(layout_id)

    def list_for_workspace(self, *, user_id: uuid.UUID, workspace: LayoutWorkspace):
        return [
            v for v in self._store.values() if v.user_id == user_id and v.workspace == workspace
        ]

    def get_by_name(self, *, user_id: uuid.UUID, workspace: LayoutWorkspace, name: str):
        for item in self._store.values():
            if item.user_id == user_id and item.workspace == workspace and item.name == name:
                return item
        return None

    def get_default(self, *, user_id: uuid.UUID, workspace: LayoutWorkspace):
        for item in self._store.values():
            if item.user_id == user_id and item.workspace == workspace and item.is_default:
                return item
        return None

    def create(self, data):
        item = FakeLayout(
            id=uuid.uuid4(),
            user_id=data.user_id,
            workspace=data.workspace,
            name=data.name,
            layout_json=data.layout_json,
            version=data.version,
            is_default=data.is_default,
        )
        self._store[item.id] = item
        return item

    def update_layout(self, *, layout_id: uuid.UUID, name, layout_json: dict, version: int):
        item = self._store[layout_id]
        if name is not None:
            item.name = name
        item.layout_json = layout_json
        item.version = version

    def clear_default_for_workspace(self, *, user_id: uuid.UUID, workspace: LayoutWorkspace):
        for item in self._store.values():
            if item.user_id == user_id and item.workspace == workspace:
                item.is_default = False

    def set_default(self, *, user_id: uuid.UUID, workspace: LayoutWorkspace, layout_id: uuid.UUID):
        self.clear_default_for_workspace(user_id=user_id, workspace=workspace)
        self._store[layout_id].is_default = True

    def delete(self, *, layout_id: uuid.UUID, user_id: uuid.UUID):
        item = self._store.get(layout_id)
        if item and item.user_id == user_id:
            del self._store[layout_id]


class FakeAuditRepo:
    def __init__(self, _session, sink: list[str]) -> None:
        self._sink = sink

    def write(self, entry):
        self._sink.append(entry.action)


@pytest.fixture()
def fake_env(monkeypatch):
    store: dict[uuid.UUID, FakeLayout] = {}
    audits: list[str] = []

    @contextmanager
    def fake_scope():
        yield FakeSession()

    monkeypatch.setattr(layout_module, "session_scope", fake_scope)
    monkeypatch.setattr(layout_module, "LayoutsRepo", lambda session: FakeLayoutsRepo(session, store))
    monkeypatch.setattr(layout_module, "AuditRepo", lambda session: FakeAuditRepo(session, audits))
    return store, audits


def test_save_then_load(fake_env):
    _, audits = fake_env
    svc = LayoutService()
    user_id = uuid.uuid4()

    svc.save(
        actor_id=user_id,
        workspace=LayoutWorkspace.MARKET,
        name="main",
        layout_json={"panels": [{"id": "watchlist"}]},
    )
    loaded = svc.load_layouts(actor_id=user_id, workspace=LayoutWorkspace.MARKET)

    assert len(loaded) == 1
    assert loaded[0].name == "main"
    assert loaded[0].layout_json["version"] == LAYOUT_VERSION
    assert "layout_save" in audits


def test_migrate_legacy_layout():
    old = {"widgets": [{"id": "legacy"}], "schema_version": 1, "layoutName": "old"}
    migrated = migrate_layout(old)
    assert migrated["version"] == LAYOUT_VERSION
    assert migrated["panels"] == [{"id": "legacy"}]
    assert migrated["meta"]["name"] == "old"


def test_set_default_uniqueness(fake_env):
    _, _audits = fake_env
    svc = LayoutService()
    user_id = uuid.uuid4()

    first = svc.save_as(
        actor_id=user_id,
        workspace=LayoutWorkspace.EXPLORE,
        source_layout_id=None,
        new_name="A",
        layout_json={},
    )
    second = svc.save_as(
        actor_id=user_id,
        workspace=LayoutWorkspace.EXPLORE,
        source_layout_id=None,
        new_name="B",
        layout_json={},
    )

    svc.set_default(actor_id=user_id, workspace=LayoutWorkspace.EXPLORE, layout_id=first.layout_id)
    svc.set_default(actor_id=user_id, workspace=LayoutWorkspace.EXPLORE, layout_id=second.layout_id)

    layouts = svc.load_layouts(actor_id=user_id, workspace=LayoutWorkspace.EXPLORE)
    defaults = [item for item in layouts if item.is_default]
    assert len(defaults) == 1
    assert defaults[0].layout_id == second.layout_id


def test_delete_and_reset_behavior(fake_env):
    _store, audits = fake_env
    svc = LayoutService()
    user_id = uuid.uuid4()

    keep = svc.save_as(
        actor_id=user_id,
        workspace=LayoutWorkspace.MONITOR,
        source_layout_id=None,
        new_name="keep",
        layout_json={"panels": [{"id": "k"}]},
    )
    drop = svc.save_as(
        actor_id=user_id,
        workspace=LayoutWorkspace.MONITOR,
        source_layout_id=None,
        new_name="drop",
        layout_json={"panels": [{"id": "d"}]},
    )
    svc.set_default(actor_id=user_id, workspace=LayoutWorkspace.MONITOR, layout_id=keep.layout_id)
    svc.delete(actor_id=user_id, workspace=LayoutWorkspace.MONITOR, layout_id=drop.layout_id)

    loaded = svc.load_layouts(actor_id=user_id, workspace=LayoutWorkspace.MONITOR)
    assert len(loaded) == 1
    assert loaded[0].layout_id == keep.layout_id

    reset = svc.reset_to_default(actor_id=user_id, workspace=LayoutWorkspace.MONITOR)
    assert reset["panels"] == [{"id": "k"}]
    assert "layout_delete" in audits
    assert "layout_reset" in audits
