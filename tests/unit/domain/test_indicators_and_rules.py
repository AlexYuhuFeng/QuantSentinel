import pytest

from quantsentinel.domain.alerts.rules import SUPPORTED_RULE_TYPES, apply_rules
from quantsentinel.domain.market.indicators import SUPPORTED_INDICATORS, sma


def test_indicator_registry_and_sma() -> None:
    assert set(SUPPORTED_INDICATORS) >= {"sma", "ema", "rsi", "zscore"}
    values = [1.0, 2.0, 3.0, 4.0]
    assert sma(values, window=2) == [1.0, 1.5, 2.5, 3.5]


def test_sma_rejects_non_positive_window_and_handles_empty_values() -> None:
    with pytest.raises(ValueError):
        sma([1.0], window=0)

    assert sma([], window=3) == []


def test_rule_registry_contains_7_rule_types() -> None:
    assert len(SUPPORTED_RULE_TYPES) == 7


@pytest.mark.parametrize(
    ("rule_type", "context", "expected"),
    [
        ("threshold", {"close": 10, "threshold": 8}, True),
        ("z_score", {"z": 2.2, "z_limit": 2.0}, True),
        ("volatility", {"vol": 0.04, "vol_limit": 0.03}, True),
        ("staleness", {"age_days": 3, "max_age_days": 2}, True),
        ("missing_data", {"missing": True}, True),
        ("correlation_break", {"corr": 0.1, "corr_floor": 0.2}, True),
        (
            "custom_expression",
            {"expr": "abs(ret) > 0.02 and close > ma20", "values": {"ret": 0.03, "close": 12, "ma20": 10}},
            True,
        ),
    ],
)
def test_apply_rules_for_all_7_types(rule_type: str, context: dict, expected: bool) -> None:
    assert apply_rules(rule_type, context) is expected


def test_apply_rules_rejects_unknown_rule() -> None:
    with pytest.raises(ValueError):
        apply_rules("unknown", {})
