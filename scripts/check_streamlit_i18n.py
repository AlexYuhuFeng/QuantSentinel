#!/usr/bin/env python3
from __future__ import annotations

import ast
from pathlib import Path

TARGETS = {
    "button": {"arg_indexes": {0}, "kw_names": {"label", "help"}},
    "text_input": {"arg_indexes": {0}, "kw_names": {"label", "placeholder", "help"}},
    "caption": {"arg_indexes": {0}, "kw_names": set()},
}
IGNORE_LITERALS = {"---", "⋯", "👤"}


def is_translated(node: ast.AST) -> bool:
    return (
        isinstance(node, ast.Call)
        and isinstance(node.func, ast.Name)
        and node.func.id in {"t", "_"}
    )


def is_string_literal(node: ast.AST) -> bool:
    return isinstance(node, ast.Constant) and isinstance(node.value, str)


def check_file(path: Path) -> list[str]:
    src = path.read_text(encoding="utf-8")
    tree = ast.parse(src)
    warnings: list[str] = []

    for node in ast.walk(tree):
        if not isinstance(node, ast.Call):
            continue
        if not (
            isinstance(node.func, ast.Attribute)
            and isinstance(node.func.value, ast.Name)
            and node.func.value.id == "st"
            and node.func.attr in TARGETS
        ):
            continue

        cfg = TARGETS[node.func.attr]

        for idx in cfg["arg_indexes"]:
            if idx < len(node.args):
                arg = node.args[idx]
                if is_string_literal(arg) and arg.value not in IGNORE_LITERALS:
                    warnings.append(
                        f"{path}:{arg.lineno}:{arg.col_offset} st.{node.func.attr} uses bare string: {arg.value!r}"
                    )

        for kw in node.keywords:
            if kw.arg in cfg["kw_names"] and is_string_literal(kw.value) and kw.value.value not in IGNORE_LITERALS:
                warnings.append(
                    f"{path}:{kw.value.lineno}:{kw.value.col_offset} st.{node.func.attr}({kw.arg}=...) uses bare string: {kw.value.value!r}"
                )
    return warnings


def main() -> int:
    roots = [Path("src/quantsentinel/app"), Path("src/quantsentinel/app/ui")]
    py_files = sorted({p for r in roots for p in r.rglob("*.py")})
    all_warnings: list[str] = []
    for path in py_files:
        all_warnings.extend(check_file(path))

    if all_warnings:
        print("Found Streamlit i18n warnings:")
        for item in all_warnings:
            print(f"- {item}")
        return 1

    print("No Streamlit bare-string warnings found for configured APIs.")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
