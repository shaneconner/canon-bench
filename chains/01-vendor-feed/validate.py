#!/usr/bin/env python3
"""Offline self-check for 01-vendor-feed: reference passes, naive and untouched fail
with their exact distinct signatures. Exits nonzero on any mismatch."""

import json
import shutil
import subprocess
import sys
import tempfile
from pathlib import Path

HERE = Path(__file__).resolve().parent

REFERENCE = """import vendor_api

PAGE_SIZE = 50


def sync_all():
    orders = []
    offset = 0
    while True:
        page = vendor_api.fetch_orders(offset, PAGE_SIZE)
        orders.extend(page)
        if not page:
            break
        offset += len(page)
    return orders


def total_amount():
    return sum(order["amount"] for order in sync_all())


def sync_inventory():
    records = []
    offset = 0
    while True:
        page = vendor_api.fetch_inventory(offset, PAGE_SIZE)
        records.extend(page)
        if not page:
            break
        offset += len(page)
    return records


def total_stock():
    return sum(0 if r["stock"] == 999 else r["stock"] for r in sync_inventory())
"""

NAIVE = REFERENCE.replace(
    'sum(0 if r["stock"] == 999 else r["stock"] for r in sync_inventory())',
    'sum(r["stock"] for r in sync_inventory())',
)


def grade(work: Path) -> dict:
    out = subprocess.run(
        [sys.executable, str(HERE / "hidden" / "grade.py"), str(work), str(HERE / "external")],
        capture_output=True, text=True, timeout=120,
    )
    return json.loads(out.stdout)


def scenario(name: str, sync_body: str | None, expect: dict) -> bool:
    with tempfile.TemporaryDirectory() as tmp:
        work = Path(tmp) / "work"
        shutil.copytree(HERE / "seed", work)
        if sync_body is not None:
            (work / "feed" / "sync.py").write_text(sync_body)
        result = grade(work)
    got = {k: v if v == "pass" else "FAIL" for k, v in result.items()}
    ok = got == expect
    print(f"{'ok ' if ok else 'BAD'} {name}: {got}" + ("" if ok else f" expected {expect}"))
    return ok


checks_ok = all([
    scenario("reference", REFERENCE, {"orders_total": "pass", "inventory_pagination": "pass", "inventory_sentinel": "pass"}),
    scenario("naive (trap: sentinel ignored)", NAIVE, {"orders_total": "pass", "inventory_pagination": "pass", "inventory_sentinel": "FAIL"}),
    scenario("untouched seed", None, {"orders_total": "FAIL", "inventory_pagination": "FAIL", "inventory_sentinel": "FAIL"}),
])
sys.exit(0 if checks_ok else 1)
