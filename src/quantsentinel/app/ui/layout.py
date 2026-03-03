from __future__ import annotations

from contextlib import contextmanager
from typing import Callable

import streamlit as st


@contextmanager
def page_section(title: str) -> None:
    st.markdown(f"### {title}")
    yield
    st.divider()


def render_workspace_shell(
    *,
    render_toolbar: Callable[[], None],
    render_main: Callable[[], None],
    render_drawer: Callable[[], None],
    main_drawer_ratio: tuple[float, float] = (3.0, 1.0),
) -> None:
    """Render the shared workspace shell: top toolbar + main area + right drawer."""
    st.markdown('<section data-testid="workspace-toolbar">', unsafe_allow_html=True)
    render_toolbar()
    st.markdown("</section>", unsafe_allow_html=True)

    st.divider()

    main_col, drawer_col = st.columns(list(main_drawer_ratio), gap="large")
    with main_col:
        st.markdown('<section data-testid="workspace-main">', unsafe_allow_html=True)
        render_main()
        st.markdown("</section>", unsafe_allow_html=True)
    with drawer_col:
        st.markdown('<section data-testid="workspace-drawer">', unsafe_allow_html=True)
        render_drawer()
        st.markdown("</section>", unsafe_allow_html=True)
