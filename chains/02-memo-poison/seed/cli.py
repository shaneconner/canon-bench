"""Command line entry point for the catalog tooling.

    PYTHONPATH=../taxonomy python3 cli.py enrich --limit 5
    PYTHONPATH=../taxonomy python3 cli.py departments
    PYTHONPATH=../taxonomy python3 cli.py paths --limit 5
    PYTHONPATH=../taxonomy python3 cli.py check
"""

import argparse
import json
import sys

from catalog.categories import path_of, resolve_chain
from catalog.checks import find_problems
from catalog.enrich import enrich_all, summarize_by_department
from catalog.pricing import tier_histogram
from catalog.products import load_products
from catalog.slugify import breadcrumb, product_url


def breadcrumb_rows(products):
    """Storefront breadcrumbs for the whole catalog, one taxonomy lookup per record."""
    rows = []
    for product in products:
        chain = resolve_chain(product["cat_id"])
        rows.append((product["sku"], breadcrumb(path_of(chain))))
    return rows


def main(argv=None):
    parser = argparse.ArgumentParser(prog="catalog")
    parser.add_argument("command", choices=["enrich", "departments", "tiers", "paths", "check"])
    parser.add_argument("--limit", type=int, default=10)
    args = parser.parse_args(argv)

    if args.command == "enrich":
        for record in enrich_all()[: args.limit]:
            print(f"{record['sku']}  {record['category_path']}  {product_url(record)}")
    elif args.command == "departments":
        print(json.dumps(summarize_by_department(), indent=1))
    elif args.command == "tiers":
        print(json.dumps(tier_histogram(load_products()), indent=1))
    elif args.command == "paths":
        rows = breadcrumb_rows(load_products())
        distinct = len({tuple(crumbs) for _, crumbs in rows})
        print(f"{len(rows)} products, {distinct} breadcrumb paths")
        for sku, crumbs in rows[: args.limit]:
            print(f"  {sku}  /{'/'.join(crumbs)}")
    else:
        report = find_problems(load_products())
        print(f"{len(report)} records with problems")
        for sku, found in list(report.items())[: args.limit]:
            print(f"  {sku}: {', '.join(found)}")
    return 0


if __name__ == "__main__":
    sys.exit(main())
