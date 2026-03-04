"""Alert rules."""

from __future__ import annotations

from typing import Any

from quantsentinel.domain.alerts.expression import evaluate

SUPPORTED_RULE_TYPES = (
    "threshold",
    "z_score",
    "volatility",
    "staleness",
    "missing_data",
    "correlation_break",
    "custom_expression",
)


def apply_rules(rule_type: str, context: dict[str, Any]) -> bool:
    """Evaluate one of the 7 monitor rule types in a deterministic way."""
    if rule_type not in SUPPORTED_RULE_TYPES:
        raise ValueError(f"unsupported rule_type: {rule_type}")

    if rule_type == "threshold":
        return float(context.get("close", 0)) > float(context.get("threshold", 0))
    if rule_type == "z_score":
        return abs(float(context.get("z", 0))) >= float(context.get("z_limit", 2.0))
    if rule_type == "volatility":
        return float(context.get("vol", 0)) >= float(context.get("vol_limit", 0.03))
    if rule_type == "staleness":
        return int(context.get("age_days", 0)) >= int(context.get("max_age_days", 3))
    if rule_type == "missing_data":
        return bool(context.get("missing", False))
    if rule_type == "correlation_break":
        return float(context.get("corr", 1.0)) <= float(context.get("corr_floor", 0.2))

    expr = str(context.get("expr", "False"))
    values = context.get("values", {})
    return evaluate(expr, values)
