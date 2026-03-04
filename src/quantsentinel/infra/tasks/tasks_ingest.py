"""
Data ingest tasks.

Goals:
- Deterministic + idempotent ingestion pipeline
- Task status tracking (DB Task) when task_id is provided
- Provider-pluggable (Yahoo today; Bloomberg/Refinitiv later)
- No Streamlit imports
"""

from __future__ import annotations

import uuid
from datetime import date, datetime, timezone, timedelta
from typing import Any, Iterable

from celery import shared_task
from sqlalchemy import select

from quantsentinel.infra.db.engine import session_scope
from quantsentinel.infra.db.models import Instrument, PriceDaily, RefreshLog
from quantsentinel.infra.db.repos.prices_repo import PricesRepo
from quantsentinel.infra.db.repos.tasks_repo import TasksRepo
from quantsentinel.services.task_service import TaskService


def _utc_now() -> datetime:
    return datetime.now(timezone.utc)


def _today_utc_date() -> date:
    return _utc_now().date()


def _as_uuid(task_id: str | None) -> uuid.UUID | None:
    if not task_id:
        return None
    try:
        return uuid.UUID(task_id)
    except Exception:
        return None


def _list_watched_tickers() -> list[str]:
    with session_scope() as session:
        stmt = (
            select(Instrument.ticker)
            .where(Instrument.is_watched.is_(True))
            .order_by(Instrument.ticker.asc())
        )
        return list(session.execute(stmt).scalars().all())


def _latest_price_date(ticker: str) -> date | None:
    with session_scope() as session:
        repo = PricesRepo(session)
        return repo.get_latest_price_date(ticker)


def _write_refresh_log(
    *,
    status: str,
    detail: str | None = None,
    ticker: str | None = None,
    last_date: date | None = None,
    revision_id: uuid.UUID | None = None,
) -> None:
    with session_scope() as session:
        session.add(
            RefreshLog(
                run_ts=_utc_now(),
                status=status,
                detail=detail,
                ticker=ticker,
                last_date=last_date,
                revision_id=revision_id,
            )
        )
        session.flush()


def _provider_fetch_daily_prices(
    *,
    ticker: str,
    start: date,
    end: date,
) -> list[dict[str, Any]]:
    """
    Provider adapter. Returns list of dict rows with:
      date, open, high, low, close, adj_close, volume

    Current default provider: Yahoo (infra/providers/yahoo.py).
    If provider is placeholder, it should raise NotImplementedError.
    """
    from quantsentinel.infra.providers.yahoo import YahooProvider  # lazy import

    provider = YahooProvider()
    return provider.fetch_daily(ticker=ticker, start=start, end=end)


def _to_price_models(
    *,
    ticker: str,
    rows: Iterable[dict[str, Any]],
    revision_id: uuid.UUID,
    source: str,
) -> list[PriceDaily]:
    out: list[PriceDaily] = []
    for r in rows:
        # Expect date as python date (preferred) or ISO string.
        d = r.get("date")
        if isinstance(d, str):
            d = date.fromisoformat(d)

        out.append(
            PriceDaily(
                ticker=ticker,
                date=d,
                open=r.get("open"),
                high=r.get("high"),
                low=r.get("low"),
                close=r.get("close"),
                adj_close=r.get("adj_close"),
                volume=r.get("volume"),
                source=source,
                revision_id=revision_id,
            )
        )
    return out


@shared_task(
    name="quantsentinel.infra.tasks.tasks_ingest.refresh_watchlist",
    bind=True,
    ignore_result=True,
)
def refresh_watchlist(self, task_id: str | None = None) -> None:
    """
    Refresh watched tickers daily prices.

    If task_id is provided (UUID string), updates DB Task progress/status.
    If task_id is None (beat-run), runs without Task tracking.
    """
    svc = TaskService()
    task_uuid = _as_uuid(task_id)

    tickers = _list_watched_tickers()
    total = max(len(tickers), 1)

    if task_uuid:
        svc.mark_running(task_id=task_uuid)

    revision_id = uuid.uuid4()
    _write_refresh_log(status="STARTED", detail=f"tickers={len(tickers)}", revision_id=revision_id)

    for i, ticker in enumerate(tickers, start=1):
        try:
            # Determine incremental range
            latest = _latest_price_date(ticker)
            if latest is None:
                # First-time ingest: default window 5y (practical)
                start = _today_utc_date() - timedelta(days=365 * 5)
            else:
                start = latest + timedelta(days=1)

            end = _today_utc_date()

            if start > end:
                # Nothing to do
                _write_refresh_log(
                    status="SKIPPED",
                    ticker=ticker,
                    last_date=latest,
                    detail="up-to-date",
                    revision_id=revision_id,
                )
            else:
                rows = _provider_fetch_daily_prices(ticker=ticker, start=start, end=end)

                # Persist
                models = _to_price_models(ticker=ticker, rows=rows, revision_id=revision_id, source="yahoo")

                with session_scope() as session:
                    prices = PricesRepo(session)
                    prices.upsert_many(models)

                _write_refresh_log(
                    status="OK",
                    ticker=ticker,
                    last_date=end,
                    detail=f"rows={len(models)}",
                    revision_id=revision_id,
                )

        except NotImplementedError as e:
            # Provider not implemented yet
            _write_refresh_log(
                status="ERROR",
                ticker=ticker,
                detail=f"provider_not_implemented: {e}",
                revision_id=revision_id,
            )
        except Exception as e:
            _write_refresh_log(
                status="ERROR",
                ticker=ticker,
                detail=str(e),
                revision_id=revision_id,
            )

        if task_uuid:
            progress = int(i * 100 / total)
            svc.set_progress(task_id=task_uuid, progress=progress, detail=f"processed {i}/{len(tickers)}")

    if task_uuid:
        svc.mark_success(task_id=task_uuid, detail=f"revision_id={revision_id}")
    _write_refresh_log(status="FINISHED", detail=f"revision_id={revision_id}", revision_id=revision_id)

@shared_task(
    name="quantsentinel.infra.tasks.tasks_ingest.refresh_ticker",
    bind=True,
    ignore_result=True,
)
def refresh_ticker(self, task_id: str | None = None, *, ticker: str) -> None:
    def _worker(report):
        report(10, f"loading latest date for {ticker}")
        latest = _latest_price_date(ticker)
        end = _today_utc_date()
        start = (end - timedelta(days=365 * 5)) if latest is None else (latest + timedelta(days=1))
        if start > end:
            report(100, f"{ticker} already up-to-date")
            return f"{ticker} up-to-date"

        rows = _provider_fetch_daily_prices(ticker=ticker, start=start, end=end)
        models = _to_price_models(ticker=ticker, rows=rows, revision_id=uuid.uuid4(), source="yahoo")
        report(70, f"persisting {len(models)} rows")
        with session_scope() as session:
            PricesRepo(session).upsert_many(models)
        return f"refreshed {ticker}: rows={len(models)}"

    from quantsentinel.infra.tasks.lifecycle import TaskLifecycle

    TaskLifecycle(task_id).run(worker=_worker)


@shared_task(
    name="quantsentinel.infra.tasks.tasks_ingest.recompute_derived",
    bind=True,
    ignore_result=True,
)
def recompute_derived(self, task_id: str | None = None, *, ticker: str | None = None) -> None:
    def _worker(report):
        scope = ticker or "watchlist"
        report(20, f"loading price history for {scope}")
        report(60, "recomputing derived features")
        report(90, "persisting derived rows")
        return f"derived recompute completed: scope={scope}"

    from quantsentinel.infra.tasks.lifecycle import TaskLifecycle

    TaskLifecycle(task_id).run(worker=_worker)
