#!/usr/bin/env python3
"""Enforce line coverage for domain + services packages."""

from __future__ import annotations

import argparse
import json
from pathlib import Path


def _is_target(path: str) -> bool:
    return "/domain/" in path or "/services/" in path


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--report", default="coverage.json")
    parser.add_argument("--min", type=float, default=90.0)
    args = parser.parse_args()

    payload = json.loads(Path(args.report).read_text())
    files = payload.get("files", {})

    covered = 0
    total = 0
    for file_path, meta in files.items():
        if not _is_target(file_path):
            continue
        summary = meta.get("summary", {})
        covered += int(summary.get("covered_lines", 0))
        total += int(summary.get("num_statements", 0))

    pct = 100.0 if total == 0 else (covered / total * 100)
    print(f"domain+services coverage: {pct:.2f}% ({covered}/{total})")

    if pct < args.min:
        print(f"ERROR: domain+services line coverage below {args.min:.2f}%")
        return 1
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
