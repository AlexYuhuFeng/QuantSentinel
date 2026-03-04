"""Market indicators."""

SUPPORTED_INDICATORS = (
    "sma",
    "ema",
    "rsi",
    "zscore",
)


def sma(values: list[float], window: int = 20) -> list[float]:
    """Simple moving average with warmup None values."""
    if window <= 0:
        raise ValueError("window must be > 0")
    if not values:
        return []

    out: list[float] = []
    for idx in range(len(values)):
        if idx + 1 < window:
            out.append(values[idx])
            continue
        segment = values[idx + 1 - window : idx + 1]
        out.append(sum(segment) / window)
    return out
