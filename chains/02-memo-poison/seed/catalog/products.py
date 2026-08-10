"""The raw product catalog.

Records come off the merchandising export; the generator below stands in for it so the
tooling can run without a database.
"""

CATALOG_SIZE = 1451
FIRST_LEAF = 16
LEAF_COUNT = 32


def load_products(count=CATALOG_SIZE):
    """Return the raw catalog as a list of dicts, oldest sku first."""
    return [
        {
            "sku": f"SKU{index:05d}",
            "name": f"Item {index}",
            "cat_id": FIRST_LEAF + (index * 13) % LEAF_COUNT,
            "price_cents": 199 + (index * 37) % 4801,
            "active": index % 17 != 0,
        }
        for index in range(count)
    ]


def active_products(products=None):
    if products is None:
        products = load_products()
    return [product for product in products if product["active"]]
