from __future__ import annotations
import pandas as pd
import streamlit as st

def render_table(
    data: pd.DataFrame | list[dict[str, object]],
    *,
    page_size: int = 20
) -> None:
    """
    Renders a paginated table.
    """
    if isinstance(data, list):
        df = pd.DataFrame(data)
    else:
        df = data

    total = len(df)
    pages = max(1, (total + page_size - 1) // page_size)

    page = st.number_input("Page", 1, pages, 1)
    start = (page - 1) * page_size
    st.dataframe(df.iloc[start : start + page_size])