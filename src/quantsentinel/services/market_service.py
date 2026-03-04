"""
Market service (watchlist + anomalies + refresh).

Strict layering:
- Service calls repos
- Service controls transaction boundary
- No direct ORM usage here
"""

from __future__ import annotations

from datetime import date, datetime
from typing import TYPE_CHECKING, Any

if TYPE_CHECKING:
    import uuid

import pandas as pd
from sqlalchemy import select

from quantsentinel.infra.db.engine import session_scope
from quantsentinel.infra.db.models import PriceDaily, UserRole
from quantsentinel.infra.db.repos.audit_repo import AuditEntryCreate, AuditRepo
from quantsentinel.infra.db.repos.instruments_repo import InstrumentsRepo
from quantsentinel.infra.db.repos.prices_repo import PricesRepo
from quantsentinel.infra.db.repos.tasks_repo import TasksRepo
from quantsentinel.services.rbac_service import AuditActionType, RBACService


def _now() -> datetime:
    return datetime.now(datetime.UTC)


class MarketService:
    """
    Market workspace orchestration.
    """

    # -----------------------------
    # Watchlist
    # -----------------------------

    def add_to_watchlist(self, *, ticker: str, actor_id: uuid.UUID | None = None, actor_role: UserRole | None = None) -> None:
        ticker = ticker.strip()
        if not ticker:
            raise ValueError("Ticker required.")
        RBACService.ensure_workspace_mutation_allowed(role=actor_role, workspace="Market", action=AuditActionType.CREATE)

        with session_scope() as session:
            inst_repo = InstrumentsRepo(session)
            audit = AuditRepo(session)

            inst_repo.ensure_exists(ticker=ticker)
            inst_repo.set_watched(ticker=ticker, is_watched=True)

            audit.write(
                AuditEntryCreate(
                    action="watchlist_add",
                    entity_type="instrument",
                    entity_id=ticker,
                    actor_id=actor_id,
                    payload={"ticker": ticker},
                    ts=_now(),
                )
            )

    def remove_from_watchlist(self, *, ticker: str, actor_id: uuid.UUID | None = None, actor_role: UserRole | None = None) -> None:
        RBACService.ensure_workspace_mutation_allowed(role=actor_role, workspace="Market", action=AuditActionType.DELETE)
        with session_scope() as session:
            inst_repo = InstrumentsRepo(session)
            audit = AuditRepo(session)

            inst_repo.set_watched(ticker=ticker, is_watched=False)

            audit.write(
                AuditEntryCreate(
                    action="watchlist_remove",
                    entity_type="instrument",
                    entity_id=ticker,
                    actor_id=actor_id,
                    payload={"ticker": ticker},
                    ts=_now(),
                )
            )

    def get_watchlist(self) -> list[dict[str, Any]]:
        with session_scope() as session:
            inst_repo = InstrumentsRepo(session)
            price_repo = PricesRepo(session)

            instruments = inst_repo.list_watched()

            out: list[dict[str, Any]] = []

            for inst in instruments:
                last, prev = price_repo.get_latest_two_closes(inst.ticker)

                chg = None
                if last is not None and prev is not None:
                    chg = float(last) - float(prev)

                out.append(
                    {
                        "ticker": inst.ticker,
                        "name": inst.name,
                        "last": None if last is None else float(last),
                        "chg": chg,
                    }
                )

            return out

    # -----------------------------
    # Async refresh
    # -----------------------------

    def get_price_series(self, *, ticker: str, start: date, end: date) -> pd.DataFrame:
        ticker = ticker.strip().upper()
        if not ticker:
            raise ValueError("Ticker required.")
        if start > end:
            raise ValueError("Start date must be <= end date.")

        with session_scope() as session:
            stmt = (
                select(
                    PriceDaily.date,
                    PriceDaily.open,
                    PriceDaily.high,
                    PriceDaily.low,
                    PriceDaily.close,
                    PriceDaily.volume,
                )
                .where(
                    PriceDaily.ticker == ticker,
                    PriceDaily.date >= start,
                    PriceDaily.date <= end,
                )
                .order_by(PriceDaily.date.asc())
            )
            rows = session.execute(stmt).all()

        columns = ["date", "open", "high", "low", "close", "volume"]
        if not rows:
            return pd.DataFrame(columns=columns)

        return pd.DataFrame(rows, columns=columns)

    def refresh_watchlist_async(self, *, actor_id: uuid.UUID | None = None, actor_role: UserRole | None = None) -> uuid.UUID:
        RBACService.ensure_workspace_mutation_allowed(role=actor_role, workspace="Market", action=AuditActionType.RUN)
        with session_scope() as session:
            task_repo = TasksRepo(session)
            audit = AuditRepo(session)

            task_id = task_repo.create_task(
                task_type="refresh_watchlist",
                actor_id=actor_id,
            )

            audit.write(
                AuditEntryCreate(
                    action="task_queued",
                    entity_type="task",
                    entity_id=str(task_id),
                    actor_id=actor_id,
                    payload={"task_type": "refresh_watchlist"},
                    ts=_now(),
                )
            )

            return task_id

    # -----------------------------
    # Anomalies
    # -----------------------------

    def get_anomalies(self) -> list[dict[str, Any]]:
        STALE_DAYS = 7

        with session_scope() as session:
            inst_repo = InstrumentsRepo(session)
            price_repo = PricesRepo(session)

            watched = inst_repo.list_watched()

            out: list[dict[str, Any]] = []

            for inst in watched:
                latest_date = price_repo.get_latest_price_date(inst.ticker)

                if latest_date is None:
                    out.append(
                        {
                            "id": f"missing:{inst.ticker}",
                            "title": "Missing data",
                            "detail": f"No daily prices found for {inst.ticker}",
                            "ticker": inst.ticker,
                            "kind": "missing_data",
                        }
                    )
                    continue

                age = (datetime.now().date() - latest_date).days
                if age >= STALE_DAYS:
                    out.append(
                        {
                            "id": f"stale:{inst.ticker}",
                            "title": "Stale data",
                            "detail": f"{inst.ticker} last updated {age} days ago.",
                            "ticker": inst.ticker,
                            "kind": "stale",
                        }
                    )

            return out
