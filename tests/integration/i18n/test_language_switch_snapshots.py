from __future__ import annotations

import sys
from dataclasses import dataclass
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[3] / "src"))

from quantsentinel.i18n.gettext import get_translator


@dataclass(frozen=True)
class RenderSnapshot:
    login: tuple[str, ...]
    header: tuple[str, ...]
    market: tuple[str, ...]
    monitor: tuple[str, ...]


def _render_snapshot(language: str) -> RenderSnapshot:
    """
    Minimal reproducible rendering context.

    We intentionally snapshot translated labels that are used by key pages:
    login/header + two workspace pages (market/monitor).
    """
    t = get_translator(language)
    return RenderSnapshot(
        login=(
            t("Username or email"),
            t("Password"),
            t("Sign in"),
            t("Bootstrap admin"),
        ),
        header=(
            t("Terminal context"),
            t("Workspace"),
            t("Language"),
            t("Role"),
            t("Sign out"),
        ),
        market=(
            t("Market"),
            t("Refresh"),
            t("Export snapshot"),
            t("Watchlist"),
            t("Anomalies"),
        ),
        monitor=(
            t("Monitor Alerts"),
            t("Alert Rules"),
            t("Recent Alert Events"),
        ),
    )


def _export_payload_snapshot(language: str) -> dict[str, object]:
    """
    Minimal export/snapshot content contract.

    This validates that exported title/labels change when language switches.
    """
    t = get_translator(language)
    return {
        "title": t("Export snapshot"),
        "labels": [t("Watchlist"), t("Anomalies"), t("Refresh")],
    }


def test_language_switch_changes_key_page_texts() -> None:
    en_snapshot = _render_snapshot("en")
    zh_snapshot = _render_snapshot("zh_CN")

    assert en_snapshot.login != zh_snapshot.login
    assert en_snapshot.header != zh_snapshot.header
    assert en_snapshot.market != zh_snapshot.market
    assert en_snapshot.monitor != zh_snapshot.monitor

    assert "Sign in" in en_snapshot.login
    assert "登录" in zh_snapshot.login

    assert "Language" in en_snapshot.header
    assert "语言" in zh_snapshot.header

    assert "Export snapshot" in en_snapshot.market
    assert "导出快照" in zh_snapshot.market


def test_export_snapshot_labels_change_with_language() -> None:
    en_payload = _export_payload_snapshot("en")
    zh_payload = _export_payload_snapshot("zh_CN")

    assert en_payload["title"] != zh_payload["title"]
    assert en_payload["labels"] != zh_payload["labels"]

    assert en_payload["title"] == "Export snapshot"
    assert zh_payload["title"] == "导出快照"
