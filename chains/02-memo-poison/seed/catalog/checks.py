"""Weekly data-quality job: structural checks plus category checks over catalog records."""

from catalog.categories import department_of, path_of, resolve_chain

REQUIRED = ("sku", "name", "cat_id", "price_cents", "active")
MAX_PRICE_CENTS = 500000
MIN_CHAIN_DEPTH = 3
DEPARTMENTS = ("Apparel", "Grocery", "Home", "Outdoors")


def problems_for(product):
    """Every structural complaint about a single record, as short strings."""
    found = []
    for field in REQUIRED:
        if field not in product:
            found.append(f"missing {field}")
    sku = product.get("sku", "")
    if not sku.startswith("SKU"):
        found.append("sku prefix")
    price = product.get("price_cents")
    if not isinstance(price, int) or price <= 0:
        found.append("price not a positive integer")
    elif price > MAX_PRICE_CENTS:
        found.append("price over ceiling")
    return found


def category_problems_for(product):
    """Complaints that need the taxonomy: the record's chain must be deep and rooted.

    One lookup per record; the weekly job pays this for the whole catalog.
    """
    chain = resolve_chain(product.get("cat_id"))
    found = []
    if len(chain) < MIN_CHAIN_DEPTH:
        found.append(f"shallow category chain: {path_of(chain)}")
    if department_of(chain) not in DEPARTMENTS:
        found.append(f"unknown department: {department_of(chain)}")
    return found


def find_problems(products):
    """Map sku to complaints for every record that has any."""
    report = {}
    for product in products:
        found = problems_for(product) + category_problems_for(product)
        if found:
            report[product.get("sku", "<no sku>")] = found
    return report
