from __future__ import annotations

from datetime import date, datetime, timedelta
from types import SimpleNamespace

from quantsentinel.services.alerts_service import AlertsService


class FakePricesRepo:
    def __init__(self) -> None:
        self.today = date(2024, 1, 10)

    def get_latest_close(self, *, ticker: str):
        return self.today, 100.0

    def get_return_stats(self, *, ticker: str, lookback: int):
        if ticker == "VOL":
            return 0.0, 0.05
        return 0.0, 0.01

    def get_pct_change_over_days(self, *, ticker: str, days: int):
        if ticker == "ZS":
            return self.today, 4.0
        return self.today, 1.0

    def get_latest_price_date(self, ticker: str):
        if ticker == "STALE":
            return self.today - timedelta(days=20)
        return self.today

    def get_recent_closes(self, *, ticker: str, days: int):
        if ticker == "MISS":
            return [(self.today, 100.0)] * 3
        if ticker == "BENCH":
            return [(self.today, x) for x in [100, 101, 102, 103, 104]]
        if ticker == "CORR":
            return [(self.today, x) for x in [100, 95, 105, 90, 110]]
        return [(self.today, x) for x in [100, 101, 102, 103, 104]]


def _rule(rule_type: str, params: dict):
    return SimpleNamespace(rule_type=rule_type, params_json=params)


def test_evaluate_all_seven_rule_types() -> None:
    svc = AlertsService()
    prices = FakePricesRepo()
    assert svc._evaluate_rule(rule=_rule("threshold", {"operator": ">", "value": 90}), ticker="AAPL", prices_repo=prices)
    assert svc._evaluate_rule(rule=_rule("z_score", {"lookback": 20, "threshold": 2}), ticker="ZS", prices_repo=prices)
    assert svc._evaluate_rule(rule=_rule("volatility", {"lookback": 20, "threshold": 0.03}), ticker="VOL", prices_repo=prices)
    assert svc._evaluate_rule(rule=_rule("staleness", {"max_days": 7}), ticker="STALE", prices_repo=prices)
    assert svc._evaluate_rule(rule=_rule("missing_data", {"lookback_days": 10, "min_points": 5}), ticker="MISS", prices_repo=prices)
    assert svc._evaluate_rule(
        rule=_rule("correlation_break", {"benchmark_ticker": "BENCH", "lookback": 4, "min_corr": 0.2}),
        ticker="CORR",
        prices_repo=prices,
    )
    assert svc._evaluate_rule(
        rule=_rule("custom_expression", {"expression": "close > 50 and abs(z) >= 0"}),
        ticker="AAPL",
        prices_repo=prices,
    )


def test_is_deduped_uses_events_repo_lookup() -> None:
    svc = AlertsService()
    called = {}

    class EventsRepoStub:
        def exists_recent(self, **kwargs):
            called.update(kwargs)
            return True

    policy = SimpleNamespace(dedup_minutes=30, aggregation_key="bucket")
    rule = SimpleNamespace(id="r-1")
    assert svc._is_deduped(rule=rule, ticker="AAPL", events_repo=EventsRepoStub(), policy=policy)
    assert called["window_minutes"] == 30
    assert called["aggregation_key"] == "bucket"
