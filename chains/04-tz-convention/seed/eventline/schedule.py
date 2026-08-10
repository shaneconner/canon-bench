"""Recurrence maths for repeating events."""

from datetime import timedelta


def next_occurrences(start, every_days, count):
    """The ``count`` occurrences after ``start``, spaced ``every_days`` apart."""
    if every_days < 1:
        raise ValueError("every_days must be at least 1")
    return [start + timedelta(days=every_days * step) for step in range(1, count + 1)]


def occurrences_between(start, every_days, low, high):
    """Every occurrence of the series in [low, high], ``start`` included."""
    if every_days < 1:
        raise ValueError("every_days must be at least 1")
    out = []
    current = start
    while current <= high:
        if current >= low:
            out.append(current)
        current = current + timedelta(days=every_days)
    return out


def expand(event, every_days, count):
    """Materialise a repeating event into ``count`` follow-up records."""
    out = []
    for index, stamp in enumerate(next_occurrences(event["starts_at"], every_days, count), 1):
        clone = dict(event)
        clone["id"] = f"{event['id']}-r{index}"
        clone["starts_at"] = stamp
        out.append(clone)
    return out
