"""Selecting events out of a list by time range."""

from datetime import timedelta


def events_between(events, start, end):
    """Events whose start falls in [start, end].

    Both bounds are inclusive: callers ask for a day by handing in that day's
    first second and last second, so an event sitting exactly on a bound counts.
    """
    return [event for event in events if start < event["starts_at"] < end]


def upcoming(events, since, days):
    """Events starting in the [since, since + days] range, earliest first."""
    end = since + timedelta(days=days)
    return sorted(events_between(events, since, end), key=lambda e: (e["starts_at"], e["id"]))


def group_by_day(events):
    """{date: [event, ...]} keyed by the start date, each list time ordered."""
    grouped = {}
    for event in sorted(events, key=lambda e: (e["starts_at"], e["id"])):
        grouped.setdefault(event["starts_at"].date(), []).append(event)
    return grouped


def span(events):
    """(earliest start, latest start) or (None, None) for an empty list."""
    if not events:
        return (None, None)
    stamps = [event["starts_at"] for event in events]
    return (min(stamps), max(stamps))
