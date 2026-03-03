"""
Instruments repository.

Responsibilities:
- CRUD/query for Instrument table only
- No business logic (no provider calls, no analytics)
- Session injected; commit controlled by service/session_scope
"""

from __future__ import annotations

from dataclasses import dataclass

from sqlalchemy import select, update
from sqlalchemy.orm import Session

from quantsentinel.infra.db.models import Instrument


@dataclass(frozen=True)
class InstrumentUpsert:
    ticker: str
    name: str | None = None
    exchange: str | None = None
    currency: str | None = None
    source: str | None = None


class InstrumentsRepo:
    def __init__(self, session: Session) -> None:
        self._session = session

    def get(self, ticker: str) -> Instrument | None:
        return self._session.get(Instrument, ticker)

    def ensure_exists(self, *, ticker: str) -> Instrument:
        """
        Ensure an instrument row exists; creates a minimal row if missing.
        """
        ticker = (ticker or "").strip()
        if not ticker:
            raise ValueError("ticker required")

        inst = self._session.get(Instrument, ticker)
        if inst is not None:
            return inst

        inst = Instrument(
            ticker=ticker,
            name=None,
            exchange=None,
            currency=None,
            is_watched=False,
            source=None,
        )
        self._session.add(inst)
        self._session.flush()
        return inst

    def upsert_metadata(self, data: InstrumentUpsert) -> Instrument:
        """
        Upsert basic instrument metadata (name/exchange/currency/source).
        """
        ticker = (data.ticker or "").strip()
        if not ticker:
            raise ValueError("ticker required")

        inst = self._session.get(Instrument, ticker)
        if inst is None:
            inst = Instrument(
                ticker=ticker,
                name=data.name,
                exchange=data.exchange,
                currency=data.currency,
                is_watched=False,
                source=data.source,
            )
            self._session.add(inst)
            self._session.flush()
            return inst

        # Update only if provided (keep existing if None)
        if data.name is not None:
            inst.name = data.name
        if data.exchange is not None:
            inst.exchange = data.exchange
        if data.currency is not None:
            inst.currency = data.currency
        if data.source is not None:
            inst.source = data.source

        self._session.flush()
        return inst

    def set_watched(self, *, ticker: str, is_watched: bool) -> None:
        ticker = (ticker or "").strip()
        if not ticker:
            raise ValueError("ticker required")

        stmt = update(Instrument).where(Instrument.ticker == ticker).values(is_watched=is_watched)
        self._session.execute(stmt)

    def list_watched(self, *, limit: int = 200) -> list[Instrument]:
        stmt = (
            select(Instrument)
            .where(Instrument.is_watched.is_(True))
            .order_by(Instrument.ticker.asc())
            .limit(limit)
        )
        return list(self._session.execute(stmt).scalars().all())