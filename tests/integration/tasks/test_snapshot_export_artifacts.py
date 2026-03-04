from __future__ import annotations

import json
from pathlib import Path

from quantsentinel.infra.tasks.tasks_snapshot import export_snapshot


class _FakeScope:
    def __enter__(self):
        return object()

    def __exit__(self, exc_type, exc, tb):
        return False


class _FakeAuditRepo:
    entries: list[object] = []

    def __init__(self, _session) -> None:
        pass

    def write(self, entry) -> None:
        self.entries.append(entry)


def test_export_snapshot_writes_json_html_and_metadata(monkeypatch, tmp_path: Path) -> None:
    artifacts_dir = tmp_path / "artifacts"

    monkeypatch.setattr("quantsentinel.infra.tasks.tasks_snapshot.ARTIFACTS_DIR", artifacts_dir)
    monkeypatch.setattr("quantsentinel.infra.tasks.tasks_snapshot.session_scope", lambda: _FakeScope())
    monkeypatch.setattr("quantsentinel.infra.tasks.tasks_snapshot.AuditRepo", _FakeAuditRepo)

    task_id = "task-123"
    export_snapshot.run(
        task_id=task_id,
        scope="all",
        workspace="workspace-alpha",
        ticker="AAPL",
        as_of_date="2024-02-01",
        language="zh-CN",
    )

    json_files = sorted(artifacts_dir.glob(f"snapshot_{task_id}_*.json"))
    html_files = sorted(artifacts_dir.glob(f"snapshot_{task_id}_*.html"))

    assert len(json_files) == 1
    assert len(html_files) == 1

    payload = json.loads(json_files[0].read_text(encoding="utf-8"))
    assert payload["context"] == {
        "workspace": "workspace-alpha",
        "ticker": "AAPL",
        "date": "2024-02-01",
        "language": "zh-CN",
    }

    metadata = payload["metadata"]
    assert metadata["data_revision_id"]
    assert metadata["code_hash"]
    assert metadata["language"] == "zh-CN"
    assert metadata["exported_at"]

    html_text = html_files[0].read_text(encoding="utf-8")
    assert "QuantSentinel Snapshot Report" in html_text
    assert "Key KPIs" in html_text
    assert "Chart Summary" in html_text

    assert _FakeAuditRepo.entries, "expected audit log to be written"
    latest_entry = _FakeAuditRepo.entries[-1]
    assert latest_entry.action == "export_snapshot"
    assert latest_entry.entity_type == "snapshot"
