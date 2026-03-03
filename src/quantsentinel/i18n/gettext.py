"""
gettext wrapper for QuantSentinel.

Usage:
    from quantsentinel.i18n.gettext import get_translator
    t = get_translator("zh_CN")
    t("Market")

Notes:
- Streamlit has no built-in i18n; gettext is stable and scalable.
- This module must have zero Streamlit dependencies.
"""

from __future__ import annotations

import ast
import gettext
from functools import lru_cache
from pathlib import Path

# Project root = .../src/quantsentinel/i18n/gettext.py -> .../ (project root)
_PROJECT_ROOT = Path(__file__).resolve().parents[3]
_LOCALES_DIR = _PROJECT_ROOT / "locales"
_DOMAIN = "quantsentinel"


class _CatalogTranslations(gettext.NullTranslations):
    def __init__(self, catalog: dict[str, str]) -> None:
        super().__init__()
        self._catalog = catalog

    def gettext(self, message: str) -> str:
        return self._catalog.get(message, message)


def normalize_language(lang: str) -> str:
    """
    Normalize language codes used by the app.
    """
    if not lang:
        return "en"
    lang = lang.strip()
    if lang.lower() in {"zh", "zh-cn", "zh_cn", "zh-hans"}:
        return "zh_CN"
    if lang.lower() in {"en", "en-us", "en_us"}:
        return "en"
    return lang


def _unquote_po_string(raw: str) -> str:
    return ast.literal_eval(raw)


def _load_po_catalog(lang: str) -> dict[str, str]:
    po_path = _LOCALES_DIR / lang / "LC_MESSAGES" / f"{_DOMAIN}.po"
    if not po_path.exists():
        return {}

    catalog: dict[str, str] = {}
    current_msgid: str | None = None

    for line in po_path.read_text(encoding="utf-8").splitlines():
        stripped = line.strip()
        if not stripped or stripped.startswith("#"):
            continue

        if stripped.startswith("msgid "):
            current_msgid = _unquote_po_string(stripped[6:].strip())
            continue

        if stripped.startswith("msgstr ") and current_msgid is not None:
            msgstr = _unquote_po_string(stripped[7:].strip())
            if current_msgid:
                catalog[current_msgid] = msgstr or current_msgid
            current_msgid = None

    return catalog


@lru_cache(maxsize=16)
def _load_translation(lang: str) -> gettext.NullTranslations:
    """
    Load translation catalog.

    Preferred order:
    1) gettext compiled catalog (.mo)
    2) source catalog (.po) parsed as a fallback
    3) NullTranslations (identity)
    """
    lang = normalize_language(lang)

    try:
        return gettext.translation(
            domain=_DOMAIN,
            localedir=str(_LOCALES_DIR),
            languages=[lang],
            fallback=False,
        )
    except Exception:
        catalog = _load_po_catalog(lang)
        if catalog:
            return _CatalogTranslations(catalog)
        return gettext.NullTranslations()


def get_translator(lang: str):
    """
    Returns a callable t(msgid) -> translated string.
    """
    trans = _load_translation(lang)
    return trans.gettext
