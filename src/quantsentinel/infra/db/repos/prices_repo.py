"""
Prices repository.

Responsibilities:
- CRUD/query for PriceDaily only
- No provider/network calls
- No indicator calculations
"""

from __future__ import annotations

from dataclasses import dataclass
from datetime import date
from decimal import Decimal
from typing import Iterable

from sqlalchemy import delete, select
from sqlalchemy.orm import Session

from quantsentinel.infra.db.models import PriceDaily


@dataclass(frozen=True)
class PriceDailyCreate:
    ticker: str
    date: date
    open: Decimal | None = None
    high: Decimal | None = None
    low: Decimal | None = None
    close: Decimal | None = None
    adj_close: Decimal | None = None
    volume: Decimal | None = None
    source: str = "unknown"
    revision_id: object = None  # uuid.UUID typically; kept generic to avoid importing uuid here


class PricesRepo:
    def __init__(self, session: Session) -> None:
        self._session = session

    # -----------------------------
    # Read helpers used by Market
    # -----------------------------

    def get_latest_price_date(self, ticker: str) -> date | None:
        stmt = (
            select(PriceDaily.date)
            .where(PriceDaily.ticker == ticker)
            .order_by(PriceDaily.date.desc())
            .limit(1)
        )
        return self._session.execute(stmt).scalar_one_or_none()

    def get_latest_two_closes(self, ticker: str) -> tuple[Decimal | None, Decimal | None]:
        """
        Returns (latest_close, previous_close)
        """
        stmt = (
            select(PriceDaily.close)
            .where(PriceDaily.ticker == ticker)
            .order_by(PriceDaily.date.desc())
            .limit(2)
        )
        closes = list(self._session.execute(stmt).scalars().all())
        last = closes[0] if len(closes) >= 1 else None
        prev = closes[1] if len(closes) >= 2 else None
        return last, prev

    # -----------------------------
    # Write / maintenance (for ingest)
    # -----------------------------

    def delete_range(self, *, ticker: str, start: date, end: date) -> int:
        """
        Delete prices for ticker in [start, end].
        Returns affected row count (if DB supports it).
        """
        stmt = delete(PriceDaily).where(
            PriceDaily.ticker == ticker,
            PriceDaily.date >= start,
            PriceDaily.date <= end,
        )
        res = self._session.execute(stmt)
        try:
            return int(res.rowcount or 0)
        except Exception:
            return 0

    def upsert_many(self, rows: Iterable[PriceDaily]) -> None:
        """
        Add many PriceDaily ORM rows. Caller is responsible for handling conflicts.

        Note:
        - For large ingest we will later implement a Postgres ON CONFLICT DO UPDATE path.
        """
        self._session.add_all(list(rows))
        self._session.flush()