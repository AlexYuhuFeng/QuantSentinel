"""Safe alert expression evaluation helpers."""

from __future__ import annotations

import ast
from collections.abc import Mapping
from typing import Any

_ALLOWED_VARIABLES = {"close", "ret", "vol", "z", "ma20", "ma60"}
_ALLOWED_FUNCTIONS = {"abs": abs, "min": min, "max": max}
_FORBIDDEN_NAMES = {"eval", "exec", "__import__"}
_ALLOWED_NODES = {
    ast.Expression,
    ast.BoolOp,
    ast.BinOp,
    ast.UnaryOp,
    ast.Compare,
    ast.Name,
    ast.Load,
    ast.Constant,
    ast.Call,
    ast.And,
    ast.Or,
    ast.Not,
    ast.Add,
    ast.Sub,
    ast.Mult,
    ast.Div,
    ast.Mod,
    ast.Pow,
    ast.USub,
    ast.UAdd,
    ast.Eq,
    ast.NotEq,
    ast.Gt,
    ast.GtE,
    ast.Lt,
    ast.LtE,
    ast.IfExp,
}


class ExpressionValidationError(ValueError):
    """Raised when an expression violates safety rules."""


def _validate_ast(node: ast.AST) -> None:
    for current in ast.walk(node):
        if isinstance(current, ast.Import | ast.ImportFrom | ast.Attribute | ast.Subscript | ast.Lambda):
            raise ExpressionValidationError(f"Forbidden syntax: {type(current).__name__}")

        if type(current) not in _ALLOWED_NODES:
            raise ExpressionValidationError(f"Unsupported syntax: {type(current).__name__}")

        if isinstance(current, ast.Name) and current.id not in _ALLOWED_VARIABLES | set(_ALLOWED_FUNCTIONS):
            if current.id in _FORBIDDEN_NAMES:
                raise ExpressionValidationError(f"Forbidden name: {current.id}")
            raise ExpressionValidationError(f"Variable/function '{current.id}' is not allowed")

        if isinstance(current, ast.Call):
            if not isinstance(current.func, ast.Name):
                raise ExpressionValidationError("Only direct function calls are allowed")
            if current.func.id in _FORBIDDEN_NAMES:
                raise ExpressionValidationError(f"Forbidden function: {current.func.id}")
            if current.func.id not in _ALLOWED_FUNCTIONS:
                raise ExpressionValidationError(f"Function '{current.func.id}' is not allowed")
            if current.keywords:
                raise ExpressionValidationError("Keyword arguments are not allowed")


def evaluate(expr: str, values: Mapping[str, float | int] | None = None) -> bool:
    """Evaluate an alert expression against a constrained variable context."""
    parsed = ast.parse(expr, mode="eval")
    _validate_ast(parsed)

    context: dict[str, Any] = {name: 0.0 for name in _ALLOWED_VARIABLES}
    if values:
        unknown = set(values) - _ALLOWED_VARIABLES
        if unknown:
            unknown_fmt = ", ".join(sorted(unknown))
            raise ExpressionValidationError(f"Unknown variables provided: {unknown_fmt}")
        context.update(values)

    code = compile(parsed, "<alert-expression>", "eval")
    result = eval(code, {"__builtins__": {}}, {**_ALLOWED_FUNCTIONS, **context})
    return bool(result)
