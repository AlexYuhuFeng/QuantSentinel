"""Runs repository."""

from __future__ import annotations

from decimal import Decimal
from typing import TYPE_CHECKING, Any

from sqlalchemy import select

from quantsentinel.infra.db.models import StrategyRun

if TYPE_CHECKING:
    from datetime import date

    from sqlalchemy.orm import Session


class RunsRepo:
    def __init__(self, session: Session) -> None:
        self._session = session

    def create_strategy_run(
        self,
        *,
        family: str,
        params_json: dict[str, Any],
        metrics_json: dict[str, Any],
        artifacts_json: dict[str, Any],
        start_date: date | None,
        end_date: date | None,
        score: float,
        random_seed: int | None,
    ) -> StrategyRun:
        row = StrategyRun(
            family=family,
            params_json=params_json,
            metrics_json=metrics_json,
            artifacts_json=artifacts_json,
            start_date=start_date,
            end_date=end_date,
            score=Decimal(str(round(score, 8))),
            random_seed=random_seed,
        )
        self._session.add(row)
        self._session.flush()
        return row

    def list_by_family(self, *, family: str, limit: int = 50) -> list[StrategyRun]:
        stmt = select(StrategyRun).where(StrategyRun.family == family).order_by(StrategyRun.created_at.desc()).limit(limit)
        return list(self._session.execute(stmt).scalars().all())
