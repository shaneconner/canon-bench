"""Daily aggregation over the ledger extract.

Everything here works in cents, the unit the feed delivers.
"""

from report import ledger


def category_rows(date):
    """One row per category for a ledger date, sorted by category name."""
    counts = {}
    amounts = {}
    for row in ledger.transactions_for(date):
        category = row["category"]
        counts[category] = counts.get(category, 0) + 1
        amounts[category] = amounts.get(category, 0) + row["amount_cents"]
    return [
        {"category": category, "count": counts[category], "amount_cents": amounts[category]}
        for category in sorted(counts)
    ]


def day_total(date):
    """Total amount for a ledger date, in cents."""
    return sum(row["amount_cents"] for row in category_rows(date))


def day_count(date):
    """Number of transactions rolled into the day's report."""
    return sum(row["count"] for row in category_rows(date))


def counts_by_date():
    """Transaction count per ledger date, for the anomaly pass."""
    return {date: day_count(date) for date in ledger.dates()}
