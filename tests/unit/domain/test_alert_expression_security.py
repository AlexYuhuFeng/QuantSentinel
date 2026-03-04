import pytest

from quantsentinel.domain.alerts.expression import ExpressionValidationError, evaluate


def test_expression_rejects_subscript_and_unknown_inputs() -> None:
    with pytest.raises(ExpressionValidationError):
        evaluate("close[0] > 1", {"close": 10})

    with pytest.raises(ExpressionValidationError):
        evaluate("close > 1", {"close": 2, "evil": 1})


def test_expression_rejects_unknown_function_and_allows_safe_function_calls() -> None:
    with pytest.raises(ExpressionValidationError):
        evaluate("sum(close, ret) > 0", {"close": 1, "ret": 2})

    assert evaluate("max(close, ma20) >= close", {"close": 10, "ma20": 9}) is True
