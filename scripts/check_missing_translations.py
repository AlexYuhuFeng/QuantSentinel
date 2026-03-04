#!/usr/bin/env python3
from __future__ import annotations

import argparse
from pathlib import Path


def parse_po(path: Path) -> list[tuple[str, str, int]]:
    entries: list[tuple[str, str, int]] = []
    msgid: str | None = None
    msgstr: str | None = None
    msgid_line = 0

    for idx, raw in enumerate(path.read_text(encoding="utf-8").splitlines(), start=1):
        line = raw.strip()
        if line.startswith("msgid "):
            msgid = line[len('msgid "'):-1]
            msgid_line = idx
            msgstr = None
        elif line.startswith("msgstr ") and msgid is not None:
            msgstr = line[len('msgstr "'):-1]
            entries.append((msgid, msgstr, msgid_line))
            msgid = None
            msgstr = None
    return entries


def _detect_language(po_path: Path) -> str | None:
    for line in po_path.read_text(encoding="utf-8").splitlines():
        stripped = line.strip()
        if stripped.startswith('"Language: ') and stripped.endswith('\\n"'):
            return stripped[len('"Language: '):-3]
    return None



def main() -> int:
    parser = argparse.ArgumentParser(
        description="Check PO file for missing translations (empty msgstr)."
    )
    parser.add_argument("po_file", help="Path to .po file")
    parser.add_argument("--strict", action="store_true", help="Also fail when msgstr == msgid.")
    args = parser.parse_args()

    po_path = Path(args.po_file)
    entries = parse_po(po_path)
    problems: list[tuple[str, str, int]] = []
    for msgid, msgstr, line in entries:
        if not msgid:
            continue
        if not msgstr:
            problems.append((msgid, msgstr, line))
        elif args.strict and msgstr == msgid:
            problems.append((msgid, msgstr, line))

    if problems:
        print(f"Found {len(problems)} high-risk translation entries:")
        for msgid, msgstr, line in problems:
            shown = msgstr if msgstr else "<empty>"
            print(f"- line {line}: msgid={msgid!r}, msgstr={shown!r}")
        return 1

    print("No high-risk missing translations found.")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
