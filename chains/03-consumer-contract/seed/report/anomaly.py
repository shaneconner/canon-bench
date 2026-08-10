"""Volume anomaly pass over per-date transaction counts.

Integer math only: a date is an outlier when its count differs from the median
count by more than TOLERANCE_PERCENT of that median.
"""

TOLERANCE_PERCENT = 20


def median(values):
    ordered = sorted(values)
    if not ordered:
        return 0
    middle = len(ordered) // 2
    if len(ordered) % 2 == 1:
        return ordered[middle]
    return (ordered[middle - 1] + ordered[middle]) // 2


def deviation_percent(value, baseline):
    if baseline == 0:
        return 0
    return abs(value - baseline) * 100 // baseline


def outliers(counts_by_date, tolerance_percent=TOLERANCE_PERCENT):
    """Dates whose count strays past the tolerance, ascending by date."""
    baseline = median(counts_by_date.values())
    flagged = []
    for date in sorted(counts_by_date):
        if deviation_percent(counts_by_date[date], baseline) > tolerance_percent:
            flagged.append(date)
    return flagged
