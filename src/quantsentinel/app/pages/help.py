from __future__ import annotations

import streamlit as st
from quantsentinel.app.ui.state import auth
from quantsentinel.i18n.gettext import get_translator

def render() -> None:
    """
    Help page: show documentation links, usage tips,
    and answers to common questions.
    """
    a = auth()
    t = get_translator(a.language)

    st.markdown(f"## {t('Help & Documentation')}")

    st.markdown(
        t(
            "Welcome to QuantSentinel! Below are resources to help you use the platform effectively."
        )
    )

    # --- Getting Started Section ---

    st.header(t("Getting Started"))

    st.markdown(
        f"""
- ⭐ **{t('Explore')}** — {t('Visualize price data and derived indicators for any ticker.')}
- 🧠 **{t('Monitor')}** — {t('View and manage rules to detect market conditions automatically.')}
- 📊 **{t('Research')}** — {t('Run backtests and analyze strategies against historical data.')}
- 🛠️ **{t('Strategy')}** — {t('Develop and test trading strategies within the integrated environment.')}
- 👤 **{t('Admin')}** — {t('Manage users, view audit logs, and configure your workspace.')}
"""
    )

    # --- Tips Section ---

    st.header(t("Tips & Tricks"))

    st.markdown(
        f"""
- {t('Use the search box to quickly find instruments or indicators.')}
- {t('Click on charts to explore data interactively.')}
- {t('Remember to refresh data before running research or alerts.')}
- {t('Use multiple filters to narrow down results in tables and logs.')}
"""
    )

    # --- FAQ Section ---

    st.header(t("Frequently Asked Questions"))

    st.markdown(f"**{t('How do I add a ticker to watchlist?')}**")
    st.markdown(t("Enter the ticker on the Market page and click Add to Watchlist."))

    st.markdown(f"**{t('What is an alert rule?')}**")
    st.markdown(
        t(
            "Alert rules let you automatically detect conditions like price moves "
            "or stale data, and they will show up under the Monitor tab."
        )
    )

    st.markdown(f"**{t('How often are alerts evaluated?')}**")
    st.markdown(
        t(
            "Alerts are evaluated on a periodic schedule, but you can also run them "
            "manually using the Monitor page control."
        )
    )

    # --- Support Links Section ---

    st.header(t("Support & Community"))

    st.markdown(
        f"""
- 🌐 **{t('Official Documentation')}** — [https://github.com/AlexYuhuFeng/QuantSentinel](https://github.com/AlexYuhuFeng/QuantSentinel)
- 📘 **{t('User Guide')}** — {t('See README and docs folder for detailed usage')}
- ❓ **{t('Report an Issue')}** — {t('Use GitHub Issues on the repo to report bugs or request features')}
"""
    )

    # --- Footer / Contact ---

    st.markdown("---")
    st.markdown(
        t(
            "If you have further questions, please contact the support team or reach out "
            "to the developers via the repository."
        )
    )