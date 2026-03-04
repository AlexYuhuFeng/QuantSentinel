from __future__ import annotations

import importlib.util
from pathlib import Path


def _load_module(path: Path, module_name: str):
    spec = importlib.util.spec_from_file_location(module_name, path)
    assert spec is not None and spec.loader is not None
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


def test_migration_revision_chain() -> None:
    base = Path("src/quantsentinel/infra/db/migrations/versions")
    m1 = _load_module(base / "0001_init_schema.py", "m0001")
    m2 = _load_module(base / "0002_add_notifications.py", "m0002")

    assert m1.revision == "0001_init_schema"
    assert m2.down_revision == m1.revision


def test_notification_migration_upgrade_downgrade_calls(monkeypatch) -> None:
    base = Path("src/quantsentinel/infra/db/migrations/versions")
    m2 = _load_module(base / "0002_add_notifications.py", "m0002b")

    calls: list[tuple[str, str]] = []

    def _create_table(name, *_args, **_kwargs):
        calls.append(("create_table", name))

    def _create_index(name, *_args, **_kwargs):
        calls.append(("create_index", name))

    def _drop_index(name, **_kwargs):
        calls.append(("drop_index", name))

    def _drop_table(name, **_kwargs):
        calls.append(("drop_table", name))

    monkeypatch.setattr(m2.op, "create_table", _create_table)
    monkeypatch.setattr(m2.op, "create_index", _create_index)
    monkeypatch.setattr(m2.op, "drop_index", _drop_index)
    monkeypatch.setattr(m2.op, "drop_table", _drop_table)

    m2.upgrade()
    m2.downgrade()

    assert ("create_table", "notifications") in calls
    assert ("create_index", "ix_notifications_status") in calls
    assert ("drop_index", "ix_notifications_status") in calls
    assert ("drop_table", "notifications") in calls
