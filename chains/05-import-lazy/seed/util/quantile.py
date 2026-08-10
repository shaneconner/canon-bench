"""Nearest-rank percentiles, so every answer is a value that was actually observed."""


def percentile(values, pct):
    if not values:
        raise ValueError("no values")
    if not 0 < pct <= 100:
        raise ValueError("pct out of range: %r" % (pct,))
    ordered = sorted(values)
    rank = (len(ordered) * pct + 99) // 100
    return ordered[rank - 1]


def spread(values):
    """p90 minus p10, the number the old dashboard called volatility."""
    return percentile(values, 90) - percentile(values, 10)
