"""
Yahoo Finance provider (daily bars).

Contract:
- fetch_daily(ticker, start, end) -> list[dict]
- Each dict: {
    "date": datetime.date,
    "open": Decimal|None,
    "high": Decimal|None,
    "low": Decimal|None,
    "close": Decimal|None,
    "adj_close": Decimal|None,
    "volume": Decimal|None,
  }

Notes:
- Uses Yahoo chart endpoint (unofficial, but widely used).
- No external dependencies (requests/yfinance not required).
- Built for robustness: timeout + retry + basic data QC.
"""

from __future__ import annotations

import json
import time
import urllib.error
import urllib.parse
import urllib.request
from dataclasses import dataclass
from datetime import date, datetime, timedelta, timezone
from decimal import Decimal
from typing import Any


class ProviderError(RuntimeError):
    pass


class ProviderRateLimited(ProviderError):
    pass


class ProviderNotFound(ProviderError):
    pass


@dataclass(frozen=True)
class YahooProviderConfig:
    timeout_seconds: float = 15.0
    max_retries: int = 3
    backoff_base_seconds: float = 1.0
    user_agent: str = "QuantSentinel/1.0 (+https://github.com/AlexYuhuFeng/QuantSentinel)"


def _to_unix_seconds(d: date) -> int:
    # Interpret date as UTC midnight
    dt = datetime(d.year, d.month, d.day, tzinfo=timezone.utc)
    return int(dt.timestamp())


def _decimal_or_none(x: Any) -> Decimal | None:
    if x is None:
        return None
    try:
        # Yahoo sometimes returns NaN as None already; handle floats/ints/strings
        if isinstance(x, (int, float)):
            # Avoid Decimal(float) binary artifacts by converting via string
            return Decimal(str(x))
        return Decimal(str(x))
    except Exception:
        return None


def _build_chart_url(ticker: str, start: date, end: date) -> str:
    # Yahoo uses period2 as exclusive; add 1 day to include end date
    period1 = _to_unix_seconds(start)
    period2 = _to_unix_seconds(end + timedelta(days=1))

    params = {
        "period1": str(period1),
        "period2": str(period2),
        "interval": "1d",
        "events": "div|split",
        "includeAdjustedClose": "true",
    }
    qs = urllib.parse.urlencode(params)
    safe_ticker = urllib.parse.quote(ticker, safe="")
    return f"https://query1.finance.yahoo.com/v8/finance/chart/{safe_ticker}?{qs}"


def _http_get_json(url: str, cfg: YahooProviderConfig) -> dict[str, Any]:
    headers = {"User-Agent": cfg.user_agent, "Accept": "application/json"}
    req = urllib.request.Request(url, headers=headers, method="GET")

    last_err: Exception | None = None
    for attempt in range(1, cfg.max_retries + 1):
        try:
            with urllib.request.urlopen(req, timeout=cfg.timeout_seconds) as resp:
                # Basic rate-limit detection by status code (urllib raises on 4xx/5xx in many cases)
                raw = resp.read().decode("utf-8")
                return json.loads(raw)
        except urllib.error.HTTPError as e:
            # Handle explicit rate limiting / not found
            if e.code in (401, 403, 429):
                last_err = ProviderRateLimited(f"Yahoo rate-limited or blocked (HTTP {e.code}).")
            elif e.code == 404:
                last_err = ProviderNotFound("Ticker not found on Yahoo.")
            else:
                last_err = ProviderError(f"Yahoo HTTP error: {e.code}")
        except Exception as e:
            last_err = e

        # backoff
        if attempt < cfg.max_retries:
            time.sleep(cfg.backoff_base_seconds * (2 ** (attempt - 1)))

    raise ProviderError(str(last_err) if last_err else "Yahoo request failed.")


class YahooProvider:
    def __init__(self, config: YahooProviderConfig | None = None) -> None:
        self._cfg = config or YahooProviderConfig()

    def fetch_daily(self, *, ticker: str, start: date, end: date) -> list[dict[str, Any]]:
        ticker = (ticker or "").strip()
        if not ticker:
            raise ValueError("ticker required")
        if start > end:
            return []

        url = _build_chart_url(ticker, start, end)
        payload = _http_get_json(url, self._cfg)

        chart = payload.get("chart") or {}
        error = chart.get("error")
        if error:
            # Yahoo sometimes returns structured errors
            msg = error.get("description") or error.get("message") or "Unknown Yahoo error"
            raise ProviderError(msg)

        result = (chart.get("result") or [None])[0]
        if not result:
            return []

        timestamps = result.get("timestamp") or []
        indicators = result.get("indicators") or {}
        quote_list = indicators.get("quote") or []
        adj_list = indicators.get("adjclose") or []

        quote = quote_list[0] if quote_list else {}
        adj = adj_list[0] if adj_list else {}

        opens = quote.get("open") or []
        highs = quote.get("high") or []
        lows = quote.get("low") or []
        closes = quote.get("close") or []
        volumes = quote.get("volume") or []
        adj_closes = adj.get("adjclose") or []

        out: list[dict[str, Any]] = []

        # Length alignment (Yahoo sometimes returns None values; keep index-safe)
        n = len(timestamps)
        for i in range(n):
            ts = timestamps[i]
            if ts is None:
                continue
            d = datetime.fromtimestamp(int(ts), tz=timezone.utc).date()

            # Filter strictly to requested [start, end]
            if d < start or d > end:
                continue

            o = opens[i] if i < len(opens) else None
            h = highs[i] if i < len(highs) else None
            l = lows[i] if i < len(lows) else None
            c = closes[i] if i < len(closes) else None
            v = volumes[i] if i < len(volumes) else None
            ac = adj_closes[i] if i < len(adj_closes) else None

            row = {
                "date": d,
                "open": _decimal_or_none(o),
                "high": _decimal_or_none(h),
                "low": _decimal_or_none(l),
                "close": _decimal_or_none(c),
                "adj_close": _decimal_or_none(ac),
                "volume": _decimal_or_none(v),
            }

            # Basic QC: if all OHLC are None, skip row
            if all(row[k] is None for k in ("open", "high", "low", "close", "adj_close")):
                continue

            out.append(row)

        # Ensure deterministic ordering
        out.sort(key=lambda r: r["date"])
        return out