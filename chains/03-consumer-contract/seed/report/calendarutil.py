"""Business-day helpers used by the older scheduling scripts.

Kept here so the reporting job and the scheduler agree on what a working day
is. Holidays are the fixed-date subset only; the movable ones never mattered
for this ledger.
"""

from datetime import date, timedelta

FIXED_HOLIDAYS = ((1, 1), (7, 4), (11, 11), (12, 25))


def parse_date(text):
    year, month, day = (int(part) for part in text.split("-"))
    return date(year, month, day)


def is_weekend(day):
    return day.weekday() >= 5


def is_holiday(day):
    return (day.month, day.day) in FIXED_HOLIDAYS


def is_business_day(day):
    return not is_weekend(day) and not is_holiday(day)


def next_business_day(day):
    candidate = day + timedelta(days=1)
    while not is_business_day(candidate):
        candidate = candidate + timedelta(days=1)
    return candidate


def business_days_between(start, end):
    """Business days in [start, end), start and end being date objects."""
    count = 0
    cursor = start
    while cursor < end:
        if is_business_day(cursor):
            count += 1
        cursor = cursor + timedelta(days=1)
    return count
