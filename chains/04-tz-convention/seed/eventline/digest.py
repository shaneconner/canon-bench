"""The nightly digest: how many events land on each day of a range."""

from datetime import datetime, time, timedelta

from . import calendarfmt, window


def day_bounds(day):
    """First and last second of ``day`` as a (start, end) pair."""
    return (datetime.combine(day, time(0, 0, 0)), datetime.combine(day, time(23, 59, 59)))


def daily_counts(events, start, end):
    """{date: count} for every day from ``start`` to ``end``, both included."""
    counts = {}
    day = start.date()
    last = end.date()
    while day <= last:
        low, high = day_bounds(day)
        counts[day] = len(window.events_between(events, low, high))
        day = day + timedelta(days=1)
    return counts


def busiest(counts):
    """(date, count) for the fullest day, ties broken by earliest date."""
    if not counts:
        return (None, 0)
    return sorted(counts.items(), key=lambda item: (-item[1], item[0]))[0]


def render(counts):
    """Digest body as a list of lines."""
    lines = []
    for day in sorted(counts):
        lines.append(f"{calendarfmt.day_label(day)}  {counts[day]:>3}")
    total = sum(counts.values())
    lines.append(f"{'total':<12}{total:>3}")
    return lines
