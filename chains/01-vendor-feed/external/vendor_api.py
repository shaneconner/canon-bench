"""Vendor SDK simulator. Stands in for the remote API; lives outside the checkout."""

_ORDERS = [{"id": i, "amount": (i * 37) % 101} for i in range(437)]
_INVENTORY = [
    {"sku": f"SKU{i:04d}", "stock": 999 if i % 9 == 0 else (i * 13) % 29}
    for i in range(361)
]


def _page(records, offset, limit):
    limit = min(limit, 50)
    return records[offset:offset + limit]


def fetch_orders(offset=0, limit=25):
    return _page(_ORDERS, offset, limit)


def fetch_inventory(offset=0, limit=25):
    return _page(_INVENTORY, offset, limit)
