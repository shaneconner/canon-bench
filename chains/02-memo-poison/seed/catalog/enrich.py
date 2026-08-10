"""Product enrichment: attach resolved category information to catalog records."""

from catalog.categories import department_of, path_of, resolve_chain
from catalog.products import load_products


def enrich_one(product):
    """Return a copy of product with category fields attached."""
    chain = resolve_chain(product["cat_id"])
    enriched = dict(product)
    enriched["category_path"] = path_of(chain)
    enriched["category"] = chain[-1]["name"]
    enriched["department"] = department_of(chain)
    return enriched


def enrich_all(products=None):
    """Enrich the whole catalog."""
    if products is None:
        products = load_products()
    return [enrich_one(product) for product in products]


def summarize_by_department(records=None):
    """Count enriched records per top level department, department name ascending."""
    if records is None:
        records = enrich_all()
    counts = {}
    for record in records:
        key = record["category"]
        counts[key] = counts.get(key, 0) + 1
    return dict(sorted(counts.items()))
