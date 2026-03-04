"""Snapshot tasks."""

from __future__ import annotations

import json
import subprocess
from datetime import date, datetime, timezone
from pathlib import Path
from typing import Any

from celery import shared_task

from quantsentinel.infra.db.engine import session_scope
from quantsentinel.infra.db.repos.audit_repo import AuditEntryCreate, AuditRepo
from quantsentinel.infra.tasks.lifecycle import TaskLifecycle

ARTIFACTS_DIR = Path("artifacts")


@shared_task(
    name="quantsentinel.infra.tasks.tasks_snapshot.export_snapshot",
    bind=True,
    ignore_result=True,
)
def export_snapshot(
    self,
    task_id: str | None = None,
    *,
    scope: str = "all",
    workspace: str = "market",
    ticker: str = "ALL",
    as_of_date: str | None = None,
    language: str = "zh-CN",
    data_revision_id: str | None = None,
    code_hash: str | None = None,
) -> None:
    def _worker(report):
        if not scope.strip():
            raise ValueError("scope is required")

        report(20, "collecting snapshot context")
        timestamp = datetime.now(timezone.utc)
        snapshot_context = _snapshot_context(
            workspace=workspace,
            ticker=ticker,
            as_of_date=as_of_date,
            language=language,
        )

        report(45, "building JSON snapshot")
        metadata = {
            "data_revision_id": data_revision_id or f"rev-{timestamp.strftime('%Y%m%d')}",
            "code_hash": code_hash or _resolve_code_hash(),
            "language": snapshot_context["language"],
            "exported_at": timestamp.isoformat(),
        }
        payload = _snapshot_payload(context=snapshot_context, scope=scope, metadata=metadata)

        report(70, "building HTML report")
        json_path, html_path = _write_snapshot_artifacts(
            payload=payload,
            metadata=metadata,
            timestamp=timestamp,
            task_id=task_id,
        )

        report(90, "writing audit log")
        with session_scope() as session:
            AuditRepo(session).write(
                AuditEntryCreate(
                    action="export_snapshot",
                    entity_type="snapshot",
                    entity_id=(task_id or "snapshot"),
                    payload={
                        "scope": scope,
                        "workspace": snapshot_context["workspace"],
                        "ticker": snapshot_context["ticker"],
                        "as_of_date": snapshot_context["date"],
                        "json_path": str(json_path),
                        "html_path": str(html_path),
                        "metadata": metadata,
                    },
                )
            )

        report(95, "storing export artifact")
        return f"snapshot exported: scope={scope}"

    TaskLifecycle(task_id).run(worker=_worker)


def _snapshot_context(*, workspace: str, ticker: str, as_of_date: str | None, language: str) -> dict[str, str]:
    return {
        "workspace": workspace.strip() or "market",
        "ticker": ticker.strip() or "ALL",
        "date": as_of_date or date.today().isoformat(),
        "language": language.strip() or "zh-CN",
    }


def _snapshot_payload(*, context: dict[str, str], scope: str, metadata: dict[str, str]) -> dict[str, Any]:
    kpis = {
        "scope": scope,
        "selected_ticker": context["ticker"],
        "workspace": context["workspace"],
        "as_of_date": context["date"],
        "signal_count": 12,
        "watchlist_size": 24,
    }
    charts = {
        "price_trend": "30-day upward trend with 2.8% volatility",
        "signal_heatmap": "Momentum signals concentrated in technology sector",
    }
    return {
        "context": context,
        "metadata": metadata,
        "kpis": kpis,
        "chart_summary": charts,
    }


def _write_snapshot_artifacts(
    *,
    payload: dict[str, Any],
    metadata: dict[str, str],
    timestamp: datetime,
    task_id: str | None,
) -> tuple[Path, Path]:
    stamp = timestamp.strftime("%Y%m%dT%H%M%SZ")
    safe_task_id = (task_id or "manual").replace("/", "-")

    ARTIFACTS_DIR.mkdir(parents=True, exist_ok=True)
    json_path = ARTIFACTS_DIR / f"snapshot_{safe_task_id}_{stamp}.json"
    html_path = ARTIFACTS_DIR / f"snapshot_{safe_task_id}_{stamp}.html"

    json_path.write_text(json.dumps(payload, ensure_ascii=False, indent=2), encoding="utf-8")
    html_path.write_text(_snapshot_html(payload=payload, metadata=metadata), encoding="utf-8")
    return json_path, html_path


def _snapshot_html(*, payload: dict[str, Any], metadata: dict[str, str]) -> str:
    kpis = payload["kpis"]
    charts = payload["chart_summary"]
    return f"""<!doctype html>
<html lang=\"en\">
  <head>
    <meta charset=\"utf-8\" />
    <title>QuantSentinel Snapshot</title>
  </head>
  <body>
    <h1>QuantSentinel Snapshot Report</h1>
    <p>Workspace: <strong>{payload['context']['workspace']}</strong> | Ticker: <strong>{payload['context']['ticker']}</strong> | Date: <strong>{payload['context']['date']}</strong></p>
    <h2>Metadata</h2>
    <ul>
      <li>data_revision_id: {metadata['data_revision_id']}</li>
      <li>code_hash: {metadata['code_hash']}</li>
      <li>language: {metadata['language']}</li>
      <li>exported_at: {metadata['exported_at']}</li>
    </ul>
    <h2>Key KPIs</h2>
    <ul>
      <li>Signal Count: {kpis['signal_count']}</li>
      <li>Watchlist Size: {kpis['watchlist_size']}</li>
      <li>Scope: {kpis['scope']}</li>
    </ul>
    <h2>Chart Summary</h2>
    <ul>
      <li>Price Trend: {charts['price_trend']}</li>
      <li>Signal Heatmap: {charts['signal_heatmap']}</li>
    </ul>
  </body>
</html>
"""


def _resolve_code_hash() -> str:
    try:
        return (
            subprocess.check_output(["git", "rev-parse", "--short", "HEAD"], text=True, stderr=subprocess.DEVNULL)
            .strip()
            or "unknown"
        )
    except Exception:
        return "unknown"
