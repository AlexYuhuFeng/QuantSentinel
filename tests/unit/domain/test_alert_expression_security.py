import pytest

from quantsentinel.domain.alerts.expression import ExpressionValidationError, evaluate


def test_expression_rejects_subscript_and_unknown_inputs() -> None:
    with pytest.raises(ExpressionValidationError):
        evaluate("close[0] > 1", {"close": 10})

    with pytest.raises(ExpressionValidationError):
        evaluate("close > 1", {"close": 2, "evil": 1})
