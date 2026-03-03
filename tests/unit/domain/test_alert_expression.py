import pytest

from quantsentinel.domain.alerts.expression import ExpressionValidationError, evaluate


def test_evaluate_valid_expression() -> None:
    ok = evaluate("abs(ret) > 0.02 and close > ma20", {"ret": 0.03, "close": 101, "ma20": 100})
    assert ok is True


def test_evaluate_rejects_malicious_expression() -> None:
    with pytest.raises(ExpressionValidationError):
        evaluate("__import__('os').system('whoami')", {"ret": 0.1})


def test_evaluate_rejects_disallowed_function() -> None:
    with pytest.raises(ExpressionValidationError):
        evaluate("sum([ret, vol]) > 1", {"ret": 0.1, "vol": 0.2})
