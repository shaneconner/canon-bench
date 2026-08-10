"""Nightly ledger extract, materialized in-repo so report runs are reproducible.

The upstream feed drops a deterministic sample here; the production job swaps
this module for the real extract loader. Amounts are whole numbers of cents,
as they arrive from the feed.
"""

DATES = ("2026-03-02", "2026-03-03", "2026-03-04", "2026-03-05")
CATEGORIES = ("fuel", "groceries", "lodging", "meals", "supplies")
EXTRACT_SIZE = 260

# The feed runs light on the last day of the window; this cycle reproduces the
# volume skew the real extract has.
DATE_CYCLE = (0, 1, 2, 3, 0, 1, 2)


def load_transactions():
    """Every transaction in the current extract, in feed order."""
    rows = []
    for i in range(EXTRACT_SIZE):
        rows.append(
            {
                "id": f"TX{i:05d}",
                "date": DATES[DATE_CYCLE[(i * 3) % len(DATE_CYCLE)]],
                "category": CATEGORIES[(i * 7) % len(CATEGORIES)],
                "amount_cents": 250 + (i * 1373) % 41000,
                "status": "void" if i % 11 == 0 else "posted",
            }
        )
    return rows


def transactions_for(date):
    """The extract narrowed to one ledger date."""
    return [row for row in load_transactions() if row["date"] == date]


def dates():
    """Ledger dates present in the extract, ascending."""
    return sorted({row["date"] for row in load_transactions()})
