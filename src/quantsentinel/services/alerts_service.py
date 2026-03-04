from __future__ import annotations

import statistics
import uuid
from dataclasses import dataclass
from datetime import datetime, timedelta, timezone
from typing import Any

from quantsentinel.domain.alerts.expression import evaluate
from quantsentinel.domain.alerts.governance import resolve_aggregation_key, should_dedup, should_silence
from quantsentinel.domain.alerts.models import GovernancePolicy
from quantsentinel.infra.db.engine import session_scope
from quantsentinel.infra.db.models import AlertEventStatus, AlertRule
from quantsentinel.infra.db.repos.alerts_repo import AlertRuleCreate, AlertRuleUpdate, AlertsRepo
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
    SUPPORTED_RULE_TYPES = {
        "threshold",
        "z_score",
        "volatility",
        "staleness",
        "missing_data",
        "correlation_break",
        "custom_expression",
    }

    @staticmethod
    def _write_audit(
        *,
        audit_repo: AuditRepo,
        action: str,
        entity_type: str,
        entity_id: str | None,
        actor_id: uuid.UUID | None,
        payload: dict[str, Any],
    ) -> None:
        audit_repo.write(
            AuditEntryCreate(
                action=action,
                entity_type=entity_type,
                entity_id=entity_id,
                actor_id=actor_id,
                payload=payload,
                ts=_now(),
            )
        )

    def list_enabled_rules(self) -> list[AlertRule]:
        with session_scope() as session:
            return AlertsRepo(session).list_enabled_rules()

    def list_recent_events(self, *, limit: int = 100):
        with session_scope() as session:
            return EventsRepo(session).list_recent(limit=limit)

    def create_rule(self, *, actor_id: uuid.UUID | None, payload: AlertRuleCreate) -> uuid.UUID:
        self._validate_rule_payload(payload.rule_type, payload.params_json or {})
        with session_scope() as session:
            repo = AlertsRepo(session)
            rule_id = repo.create_rule(payload)
            self._write_audit(
                audit_repo=AuditRepo(session),
                action="alert_rule_create",
                entity_type="alert_rule",
                entity_id=str(rule_id),
                actor_id=actor_id,
                payload={"rule_type": payload.rule_type, "name": payload.name},
            )
            return rule_id

    def update_rule(self, *, actor_id: uuid.UUID | None, rule_id: uuid.UUID, payload: AlertRuleUpdate) -> None:
        with session_scope() as session:
            AlertsRepo(session).update_rule(rule_id=rule_id, payload=payload)
            self._write_audit(
                audit_repo=AuditRepo(session),
                action="alert_rule_update",
                entity_type="alert_rule",
                entity_id=str(rule_id),
                actor_id=actor_id,
                payload={"fields": [k for k, v in payload.__dict__.items() if v is not None]},
            )

    def delete_rule(self, *, rule_id: uuid.UUID, actor_id: uuid.UUID | None = None) -> None:
        with session_scope() as session:
            AlertsRepo(session).delete_rule(rule_id=rule_id)
            self._write_audit(
                audit_repo=AuditRepo(session),
                action="alert_rule_delete",
                entity_type="alert_rule",
                entity_id=str(rule_id),
                actor_id=actor_id,
                payload={},
            )

    def set_rule_enabled(self, *, rule_id: uuid.UUID, enabled: bool, actor_id: uuid.UUID | None = None) -> None:
        with session_scope() as session:
            AlertsRepo(session).set_rule_enabled(rule_id=rule_id, enabled=enabled)
            self._write_audit(
                audit_repo=AuditRepo(session),
                action="alert_rule_update",
                entity_type="alert_rule",
                entity_id=str(rule_id),
                actor_id=actor_id,
                payload={"enabled": enabled},
            )

    def set_rule_silenced(self, *, rule_id: uuid.UUID, duration_minutes: int, actor_id: uuid.UUID | None = None) -> None:
        until = _now() + timedelta(minutes=max(duration_minutes, 1))
        with session_scope() as session:
            AlertsRepo(session).set_rule_silenced_until(rule_id=rule_id, silenced_until=until)
            self._write_audit(
                audit_repo=AuditRepo(session),
                action="alert_rule_update",
                entity_type="alert_rule",
                entity_id=str(rule_id),
                actor_id=actor_id,
                payload={"silenced_until": until.isoformat()},
            )

    def ack_event(self, *, event_id: uuid.UUID, actor_id: uuid.UUID | None = None) -> None:
        actor = actor_id or uuid.UUID("00000000-0000-0000-0000-000000000000")
        with session_scope() as session:
            EventsRepo(session).ack(event_id=event_id, actor_id=actor)
            self._write_audit(
                audit_repo=AuditRepo(session),
                action="alert_event_ack",
                entity_type="alert_event",
                entity_id=str(event_id),
                actor_id=actor_id,
                payload={},
            )

    def run_monitor_cycle(self, *, actor_id: uuid.UUID | None, task_id: uuid.UUID | None) -> dict[str, Any]:
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

            rules_evaluated = created = deduped = silenced = 0
            for idx, rule in enumerate(rules, start=1):
                rules_evaluated += 1
                policy = GovernancePolicy(
                    dedup_minutes=int((rule.params_json or {}).get("dedup_minutes", 60)),
                    aggregation_key=(rule.params_json or {}).get("aggregation_key"),
                    silenced_until=rule.silenced_until,
                )
                if should_silence(policy=policy, now=started):
                    silenced += 1
                    continue
                tickers = self._resolve_scope_tickers(rule=rule, watched=[i.ticker for i in watched])
                for ticker in tickers:
                    if self._is_deduped(rule=rule, ticker=ticker, events_repo=events_repo, policy=policy):
                        deduped += 1
                        continue
                    for hit in self._evaluate_rule(rule=rule, ticker=ticker, prices_repo=prices_repo):
                        agg_key = resolve_aggregation_key(policy=policy, ticker=ticker)
                        events_repo.create_event(
                            rule_id=rule.id,
                            ticker=agg_key,
                            message=hit["message"],
                            context=hit.get("context", {}),
                            asof_date=hit.get("asof_date"),
                            status=AlertEventStatus.NEW,
                            ack_by=None,
                        )
                        created += 1
                if task_id is not None:
                    prog = 15 + int((idx / max(len(rules), 1)) * 75)
                    task_svc.set_progress(task_id=task_id, progress=prog, detail=f"evaluated {idx}/{len(rules)} rules")

            self._write_audit(
                audit_repo=audit_repo,
                action="alert_rule_run",
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
            )

        return MonitorCycleResult(rules_evaluated, created, deduped, silenced).to_dict()

    def _resolve_scope_tickers(self, *, rule: AlertRule, watched: list[str]) -> list[str]:
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

    def _is_deduped(self, *, rule: AlertRule, ticker: str, events_repo: EventsRepo, policy: GovernancePolicy) -> bool:
        return should_dedup(
            policy=policy,
            rule_id=rule.id,
            ticker=ticker,
            dedup_lookup=events_repo.exists_recent,
        )

    def _validate_rule_payload(self, rule_type: str, params: dict[str, Any]) -> None:
        if rule_type not in self.SUPPORTED_RULE_TYPES:
            raise ValueError(f"Unsupported rule_type: {rule_type}")
        if rule_type == "custom_expression" and not str(params.get("expression", "")).strip():
            raise ValueError("custom_expression requires non-empty expression")

    def _evaluate_rule(self, *, rule: AlertRule, ticker: str, prices_repo: PricesRepo) -> list[dict[str, Any]]:
        params = rule.params_json or {}
        rtype = (rule.rule_type or "").strip()

        if rtype == "threshold":
            asof_date, last_close = prices_repo.get_latest_close(ticker=ticker)
            threshold = float(params.get("value", 0))
            op = str(params.get("operator", "<")).strip()
            if asof_date is None or last_close is None:
                return []
            value = float(last_close)
            if (op == "<" and value < threshold) or (op == ">" and value > threshold):
                return [{"message": f"{ticker}: last close {value:.4f} {op} {threshold:.4f}", "context": {"last_close": value}, "asof_date": asof_date}]
            return []

        if rtype == "z_score":
            lookback = int(params.get("lookback", 20))
            threshold = float(params.get("threshold", 2.0))
            mean, std = prices_repo.get_return_stats(ticker=ticker, lookback=lookback)
            asof_date, pct = prices_repo.get_pct_change_over_days(ticker=ticker, days=1)
            if mean is None or std in (None, 0) or pct is None:
                return []
            z = ((pct / 100.0) - mean) / std
            if abs(z) >= threshold:
                return [{"message": f"{ticker}: z-score {z:.2f} exceeds {threshold:.2f}", "context": {"z": z}, "asof_date": asof_date}]
            return []

        if rtype == "volatility":
            lookback = int(params.get("lookback", 20))
            threshold = float(params.get("threshold", 0.03))
            asof_date, _ = prices_repo.get_latest_close(ticker=ticker)
            _, std = prices_repo.get_return_stats(ticker=ticker, lookback=lookback)
            if std is not None and std >= threshold:
                return [{"message": f"{ticker}: volatility {std:.4f} >= {threshold:.4f}", "context": {"vol": std}, "asof_date": asof_date}]
            return []

        if rtype == "staleness":
            max_days = int(params.get("max_days", 7))
            latest = prices_repo.get_latest_price_date(ticker)
            if latest is None or (datetime.now().date() - latest).days >= max_days:
                return [{"message": f"{ticker}: stale data", "context": {"max_days": max_days}, "asof_date": latest}]
            return []

        if rtype == "missing_data":
            lookback = int(params.get("lookback_days", 30))
            min_points = int(params.get("min_points", lookback))
            closes = prices_repo.get_recent_closes(ticker=ticker, days=lookback)
            if len(closes) < min_points:
                return [{"message": f"{ticker}: missing data points ({len(closes)}/{min_points})", "context": {}, "asof_date": closes[-1][0] if closes else None}]
            return []

        if rtype == "correlation_break":
            benchmark = str(params.get("benchmark_ticker", ""))
            lookback = int(params.get("lookback", 20))
            threshold = float(params.get("min_corr", 0.2))
            s1 = [v for _, v in prices_repo.get_recent_closes(ticker=ticker, days=lookback + 1)]
            s2 = [v for _, v in prices_repo.get_recent_closes(ticker=benchmark, days=lookback + 1)]
            if len(s1) < 3 or len(s2) < 3:
                return []
            n = min(len(s1), len(s2))
            r1 = [(s1[i] / s1[i - 1]) - 1 for i in range(1, n) if s1[i - 1] != 0]
            r2 = [(s2[i] / s2[i - 1]) - 1 for i in range(1, n) if s2[i - 1] != 0]
            if len(r1) < 3 or len(r2) < 3:
                return []
            corr = statistics.correlation(r1[: len(r2)], r2[: len(r1)])
            asof_date, _ = prices_repo.get_latest_close(ticker=ticker)
            if corr <= threshold:
                return [{"message": f"{ticker}: corr({benchmark})={corr:.3f} <= {threshold:.3f}", "context": {"correlation": corr}, "asof_date": asof_date}]
            return []

        if rtype == "custom_expression":
            expr = str(params.get("expression", ""))
            asof_date, close = prices_repo.get_latest_close(ticker=ticker)
            _, ret_pct = prices_repo.get_pct_change_over_days(ticker=ticker, days=1)
            mean, vol = prices_repo.get_return_stats(ticker=ticker, lookback=int(params.get("lookback", 20)))
            ma20 = [x for _, x in prices_repo.get_recent_closes(ticker=ticker, days=20)]
            ma60 = [x for _, x in prices_repo.get_recent_closes(ticker=ticker, days=60)]
            ret = (ret_pct or 0.0) / 100.0
            z = 0.0 if mean is None or vol in (None, 0) else (ret - mean) / vol
            if evaluate(expr, {"close": float(close or 0), "ret": ret, "vol": float(vol or 0), "z": z, "ma20": statistics.mean(ma20) if ma20 else 0.0, "ma60": statistics.mean(ma60) if ma60 else 0.0}):
                return [{"message": f"{ticker}: custom expression triggered", "context": {"expression": expr}, "asof_date": asof_date}]
            return []

        return []
