"""Catalog test suite.

    PYTHONPATH=../taxonomy python3 tests/run_tests.py
"""

import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from catalog.checks import category_problems_for, find_problems, problems_for
from catalog.enrich import summarize_by_department
from catalog.pricing import apply_margin, format_price, tier_for
from catalog.products import active_products, load_products
from catalog.slugify import breadcrumb, product_url, slugify

DEPARTMENT_COUNTS = {"Apparel": 364, "Grocery": 362, "Home": 363, "Outdoors": 362}


def test_pricing():
    assert tier_for(999) == "budget", tier_for(999)
    assert tier_for(1000) == "standard", tier_for(1000)
    assert tier_for(20000) == "luxury", tier_for(20000)
    assert format_price(4999) == "$49.99", format_price(4999)
    assert format_price(700) == "$7.00", format_price(700)
    assert apply_margin(1000, 2500) == 1250, apply_margin(1000, 2500)
    print("pricing ok")


def test_slugify():
    assert slugify("Apparel Core") == "apparel-core", slugify("Apparel Core")
    assert slugify("  Rugs & Vases  ") == "rugs-vases", slugify("  Rugs & Vases  ")
    assert breadcrumb("Home > Home Seasonal > Bedding") == ["home", "home-seasonal", "bedding"]
    assert product_url({"name": "Item 7", "sku": "SKU00007"}) == "/p/item-7-sku00007"
    print("slugify ok")


def test_products():
    products = load_products()
    assert len(products) == 1451, len(products)
    assert len(active_products(products)) == len(products) - 86, len(active_products(products))
    assert find_problems(products) == {}, list(find_problems(products).items())[:3]
    assert problems_for({"sku": "X1"}), "problems_for should complain about a junk record"
    print("products ok")


def test_category_checks():
    products = load_products()
    assert category_problems_for(products[0]) == [], category_problems_for(products[0])
    assert category_problems_for({"sku": "SKU99999", "cat_id": 9999}), "unknown id not flagged"
    print("category checks ok")


def test_department_counts():
    counts = summarize_by_department()
    assert sum(counts.values()) == 1451, sum(counts.values())
    assert counts == DEPARTMENT_COUNTS, f"department counts: {counts}"
    print("departments ok")


def main():
    test_pricing()
    test_slugify()
    test_products()
    test_category_checks()
    test_department_counts()
    print("all catalog tests pass")


if __name__ == "__main__":
    main()
