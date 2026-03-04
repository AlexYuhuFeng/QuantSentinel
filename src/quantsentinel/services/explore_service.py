"""Exploration service"""

from __future__ import annotations

import pandas as pd


class ExploreService:
    def compute_indicators(self, df: pd.DataFrame) -> pd.DataFrame:
        expected_cols = {"date", "close"}
        missing = expected_cols - set(df.columns)
        if missing:
            missing_joined = ", ".join(sorted(missing))
            raise ValueError(f"Missing required columns: {missing_joined}")

        if df.empty:
            return pd.DataFrame(columns=["date", "returns", "rolling_vol", "zscore"])

        close = pd.to_numeric(df["close"], errors="coerce")
        returns = close.pct_change()
        rolling_vol = returns.rolling(window=20, min_periods=20).std(ddof=0)

        rolling_mean = close.rolling(window=20, min_periods=20).mean()
        rolling_std = close.rolling(window=20, min_periods=20).std(ddof=0)
        zscore = (close - rolling_mean) / rolling_std.replace(0, pd.NA)

        return pd.DataFrame(
            {
                "date": df["date"],
                "returns": returns,
                "rolling_vol": rolling_vol,
                "zscore": zscore,
            }
        )
