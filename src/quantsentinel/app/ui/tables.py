from __future__ import annotations

import pandas as pd
import streamlit as st

from quantsentinel.app.ui.state import auth
from quantsentinel.i18n.gettext import get_translator


def render_table(
    data: pd.DataFrame | list[dict[str, object]],
    *,
    page_size: int = 20
) -> None:
    """
    Renders a paginated table.
    """
    df = pd.DataFrame(data) if isinstance(data, list) else data

    t = get_translator(auth().language)

    total = len(df)
    pages = max(1, (total + page_size - 1) // page_size)
    t = get_translator(auth().language)

    page = st.number_input(t("Page"), 1, pages, 1)
    start = (page - 1) * page_size
    st.dataframe(df.iloc[start : start + page_size])
