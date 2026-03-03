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

import gettext
from functools import lru_cache
from pathlib import Path
from typing import Callable

# Project root = .../src/quantsentinel/i18n/gettext.py -> .../ (project root)
_PROJECT_ROOT = Path(__file__).resolve().parents[3]
_LOCALES_DIR = _PROJECT_ROOT / "locales"
_DOMAIN = "quantsentinel"


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


@lru_cache(maxsize=16)
def _load_translation(lang: str) -> gettext.NullTranslations:
    """
    Load translation catalog. Falls back to NullTranslations when missing.
    """
    lang = normalize_language(lang)

    try:
        return gettext.translation(
            domain=_DOMAIN,
            localedir=str(_LOCALES_DIR),
            languages=[lang],
            fallback=True,
        )
    except Exception:
        # As a hard fallback, return NullTranslations (identity function)
        return gettext.NullTranslations()


def get_translator(lang: str) -> Callable[[str], str]:
    """
    Returns a callable t(msgid) -> translated string.
    """
    trans = _load_translation(lang)
    return trans.gettext