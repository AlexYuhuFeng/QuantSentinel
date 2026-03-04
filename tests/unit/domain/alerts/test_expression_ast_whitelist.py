import pytest

from quantsentinel.domain.alerts.expression import ExpressionValidationError, evaluate


@pytest.mark.parametrize(
    ("expr", "values", "expected"),
    [
        ("close > ma20 and ma20 > ma60", {"close": 12, "ma20": 11, "ma60": 10}, True),
        ("abs(ret) > 0.01 and min(vol, z) < 1", {"ret": -0.03, "vol": 0.4, "z": 0.5}, True),
        ("max(close, ma20) == close", {"close": 12, "ma20": 11}, True),
    ],
)
def test_evaluate_allows_whitelist_ast(expr: str, values: dict[str, float], expected: bool) -> None:
    assert evaluate(expr, values) is expected


@pytest.mark.parametrize(
    "expr",
    [
        "__import__('os').system('whoami')",
        "(1).__class__",
        "eval('1+1')",
        "exec('a=1')",
        "sum([ret, vol]) > 0",
        "max(a=1, b=2)",
    ],
)
def test_evaluate_rejects_malicious_expression(expr: str) -> None:
    with pytest.raises(ExpressionValidationError):
        evaluate(expr, {"ret": 0.1, "vol": 0.2, "close": 10, "z": 1, "ma20": 9, "ma60": 8})
