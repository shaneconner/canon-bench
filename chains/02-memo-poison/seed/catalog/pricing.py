"""Price tiers and margin math for the storefront exporter."""

TIERS = ((999, "budget"), (4999, "standard"), (19999, "premium"))


def tier_for(price_cents):
    """Name the price band a record falls into."""
    for ceiling, name in TIERS:
        if price_cents <= ceiling:
            return name
    return "luxury"


def format_price(price_cents):
    """Render cents for humans."""
    return f"${price_cents // 100}.{price_cents % 100:02d}"


def apply_margin(cost_cents, margin_bps):
    """Add margin_bps basis points of margin to a cost, rounded half up."""
    return (cost_cents * (10000 + margin_bps) + 5000) // 10000


def tier_histogram(products):
    counts = {}
    for product in products:
        name = tier_for(product["price_cents"])
        counts[name] = counts.get(name, 0) + 1
    return dict(sorted(counts.items()))
