"""Price book lookups. Unrelated to the audit sink; here so the tree is real."""

BOOK = {"SKU-1": 1299, "SKU-2": 450, "SKU-3": 9900}


def price_cents(sku):
    if sku not in BOOK:
        raise KeyError(f"no price for {sku}")
    return BOOK[sku]


def discounted(sku, basis_points):
    if not 0 <= basis_points <= 10000:
        raise ValueError("basis points out of range")
    return round(price_cents(sku) * (10000 - basis_points) / 10000)
