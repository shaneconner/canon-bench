"""Rollup maths over a {host: sample} pull."""

BUSY_THRESHOLD = 70


def summarize(samples):
    """Roll one pull up into the numbers the digest prints."""
    values = list(samples.values())
    return {
        "hosts": len(samples),
        "reporting": len(values),
        "total": sum(values),
        "peak": max(values) if values else 0,
        "peak_host": max(samples, key=samples.get) if samples else None,
        "busy": sum(1 for value in values if value >= BUSY_THRESHOLD),
    }


def delta(previous, current):
    """Per-host change between two pulls; hosts missing on either side are dropped."""
    shared = set(previous) & set(current)
    return {host: current[host] - previous[host] for host in sorted(shared)}
