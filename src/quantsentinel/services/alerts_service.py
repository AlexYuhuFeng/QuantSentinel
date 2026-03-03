"""
AlertsService: orchestrates alert monitoring cycles.

Strict layering:
- Service orchestrates cross-aggregate workflow
- Domain layer evaluates rule semantics (optional; can be swapped)
- Infra repos handle persistence / queries
- No Streamlit imports

This service is called by Celery task:
  quantsentinel.infra.tasks.tasks_monitor.run_alert_monitor
"""

from __future__ import annotations

import uuid
from dataclasses import dataclass
from datetime import datetime, timezone
from typing import Any

from quantsentinel.infra.db.engine import session_scope
from quantsentinel.infra.db.models import AlertEventStatus, AlertRule
from quantsentinel.infra.db.repos.alerts_repo import AlertsRepo
from quantsentinel.infra.db.repos.audit_repo import AuditEntryCreate, AuditRepo
from quantsentinel.infra.db.repos.events_repo import EventsRepo
from quantsentinel.infra.db.repos.instruments_repo import InstrumentsRepo
from quantsentinel.infra.db.repos.prices_repo import PricesRepo
from quantsentinel.services.task_service import TaskService


def _now() -> datetime:
    return datetime.now(timezone.utc)


@dataclass(frozen=True)
class MonitorCycleResult:
    rules_evaluated: int
    events_created: int
    events_deduped: int
    events_silenced: int
    detail: str | None = None

    def to_dict(self) -> dict[str, Any]:
        return {
            "rules_evaluated": self.rules_evaluated,
            "events_created": self.events_created,
            "events_deduped": self.events_deduped,
            "events_silenced": self.events_silenced,
            "detail": self.detail,
        }


class AlertsService:
    """
    Alert monitoring orchestration.

    Expected repo APIs (we will implement them next):
      - AlertsRepo.list_enabled_rules() -> list[AlertRule]
      - InstrumentsRepo.list_watched() -> list[Instrument]
      - EventsRepo.exists_recent(rule_id, ticker, window_minutes) -> bool
      - EventsRepo.create_event(rule_id, ticker, message, context, asof_date, status, ack_by) -> uuid
    """

    def run_monitor_cycle(
        self,
        *,
        actor_id: uuid.UUID | None,
        task_id: uuid.UUID | None,
    ) -> dict[str, Any]:
        """
        Run one monitoring cycle.

        Returns a dict consumed by tasks_monitor.py:
          {
            "rules_evaluated": int,
            "events_created": int,
            "events_deduped": int,
            "events_silenced": int,
            "detail": str|None
          }
        """
        task_svc = TaskService()
        started = _now()

        if task_id is not None:
            task_svc.set_progress(task_id=task_id, progress=5, detail="loading rules")

        with session_scope() as session:
            alerts_repo = AlertsRepo(session)
            events_repo = EventsRepo(session)
            inst_repo = InstrumentsRepo(session)
            prices_repo = PricesRepo(session)
            audit_repo = AuditRepo(session)

            rules = alerts_repo.list_enabled_rules()
            watched = inst_repo.list_watched()

            if task_id is not None:
                task_svc.set_progress(
                    task_id=task_id,
                    progress=15,
                    detail=f"rules={len(rules)} watched={len(watched)}",
                )

            # Evaluate
            rules_evaluated = 0
            created = 0
            deduped = 0
            silenced = 0

            # Domain evaluator can be swapped; keep a minimal built-in evaluation for now.
            for idx, rule in enumerate(rules, start=1):
                rules_evaluated += 1

                # Governance: rule-level silence
                if rule.silenced_until is not None and rule.silenced_until > started:
                    silenced += 1
                    continue

                # Scope: by default apply to watched tickers; rule.scope_json may narrow it
                tickers = self._resolve_scope_tickers(rule=rule, watched=[i.ticker for i in watched])

                for ticker in tickers:
                    # Governance: dedup (either explicit key or implicit time window)
                    if self._is_deduped(rule=rule, ticker=ticker, events_repo=events_repo):
                        deduped += 1
                        continue

                    hits = self._evaluate_rule(
                        rule=rule,
                        ticker=ticker,
                        prices_repo=prices_repo,
                    )

                    if not hits:
                        continue

                    # For each hit, write an event (most rules create one event per ticker per cycle)
                    for hit in hits:
                        events_repo.create_event(
                            rule_id=rule.id,
                            ticker=ticker,
                            message=hit["message"],
                            context=hit.get("context", {}),
                            asof_date=hit.get("asof_date"),
                            status=AlertEventStatus.NEW,
                            ack_by=None,
                        )
                        created += 1

                # Update task progress roughly per rule
                if task_id is not None:
                    # 15..90
                    prog = 15 + int((idx / max(len(rules), 1)) * 75)
                    task_svc.set_progress(task_id=task_id, progress=prog, detail=f"evaluated {idx}/{len(rules)} rules")

            audit_repo.write(
                AuditEntryCreate(
                    action="alert_monitor_cycle",
                    entity_type="alerts",
                    entity_id=None,
                    actor_id=actor_id,
                    payload={
                        "rules": len(rules),
                        "watched": len(watched),
                        "rules_evaluated": rules_evaluated,
                        "events_created": created,
                        "events_deduped": deduped,
                        "events_silenced": silenced,
                        "ts": started.isoformat(),
                    },
                    ts=started,
                )
            )

        # Notifications are intentionally outside DB transaction boundary (best practice)
        # For now it's a stub; we'll implement NotificationService later.
        # self._notify(created_events)

        result = MonitorCycleResult(
            rules_evaluated=rules_evaluated,
            events_created=created,
            events_deduped=deduped,
            events_silenced=silenced,
            detail=None,
        )

        if task_id is not None:
            task_svc.set_progress(task_id=task_id, progress=95, detail="cycle finished")

        return result.to_dict()

    # -----------------------------
    # Governance helpers
    # -----------------------------

    def _resolve_scope_tickers(self, *, rule: AlertRule, watched: list[str]) -> list[str]:
        """
        Minimal scope resolver.

        Supported scope_json forms (extend later):
          {} -> watched
          {"tickers": ["CL=F", "NG=F"]} -> intersection with watched unless include_unwatched=true
          {"include_unwatched": true, "tickers": [...]} -> specified tickers
        """
        scope = rule.scope_json or {}
        tickers = scope.get("tickers")
        include_unwatched = bool(scope.get("include_unwatched", False))

        if not tickers:
            return watched

        tickers = [str(t).strip() for t in tickers if str(t).strip()]
        if include_unwatched:
            return tickers

        watched_set = set(watched)
        return [t for t in tickers if t in watched_set]

    def _is_deduped(self, *, rule: AlertRule, ticker: str, events_repo: EventsRepo) -> bool:
        """
        Dedup strategy:
        - If rule.params_json has {"dedup_minutes": N} use that (default 60)
        - Use EventsRepo.exists_recent(rule_id, ticker, window_minutes)
        """
        params = rule.params_json or {}
        window = int(params.get("dedup_minutes", 60))

        # If rule has a dedup_key, repos may use it internally (future improvement).
        # For now we simply check recent events for (rule_id, ticker).
        return events_repo.exists_recent(rule_id=rule.id, ticker=ticker, window_minutes=window)

    # -----------------------------
    # Rule evaluation
    # -----------------------------

    def _evaluate_rule(
        self,
        *,
        rule: AlertRule,
        ticker: str,
        prices_repo: PricesRepo,
    ) -> list[dict[str, Any]]:
        """
        Minimal built-in evaluator (extend later / swap to domain.evaluator).

        Supported rule_type (initial):
          - "pct_change_n_days": params {"days": 10, "threshold_pct": -2.0}  (e.g. 10d rolling cum drop <= -2%)
          - "last_close_below": params {"level": 100.0}
          - "data_stale_days": params {"max_days": 7}

        Output hits:
          [{"message": str, "context": {...}, "asof_date": date|None}]
        """
        params = rule.params_json or {}
        rtype = (rule.rule_type or "").strip()

        if rtype == "pct_change_n_days":
            days = int(params.get("days", 10))
            threshold_pct = float(params.get("threshold_pct", -2.0))
            # Repo method we will implement next:
            # returns: (asof_date, pct_change) where pct_change is in percent, e.g. -2.5
            asof_date, pct = prices_repo.get_pct_change_over_days(ticker=ticker, days=days)
            if asof_date is None or pct is None:
                return []
            if pct <= threshold_pct:
                return [
                    {
                        "message": f"{ticker}: {days}D change {pct:.2f}% <= {threshold_pct:.2f}%",
                        "context": {"days": days, "pct": pct, "threshold_pct": threshold_pct},
                        "asof_date": asof_date,
                    }
                ]
            return []

        if rtype == "last_close_below":
            level = float(params.get("level"))
            asof_date, last_close = prices_repo.get_latest_close(ticker=ticker)
            if asof_date is None or last_close is None:
                return []
            if float(last_close) < level:
                return [
                    {
                        "message": f"{ticker}: last close {float(last_close):.4f} < {level:.4f}",
                        "context": {"level": level, "last_close": float(last_close)},
                        "asof_date": asof_date,
                    }
                ]
            return []

        if rtype == "data_stale_days":
            max_days = int(params.get("max_days", 7))
            latest = prices_repo.get_latest_price_date(ticker)
            if latest is None:
                return [
                    {
                        "message": f"{ticker}: no price data",
                        "context": {"max_days": max_days},
                        "asof_date": None,
                    }
                ]
            age = (datetime.now().date() - latest).days
            if age >= max_days:
                return [
                    {
                        "message": f"{ticker}: stale data (age={age}d, max={max_days}d)",
                        "context": {"age_days": age, "max_days": max_days, "latest_date": latest.isoformat()},
                        "asof_date": latest,
                    }
                ]
            return []

        # Unknown rule types: do nothing (but stable)
        return []