#!/usr/bin/env python3
"""Project test suite. python3 tests/run_tests.py"""
import sys
import tempfile
from decimal import Decimal
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

from ledger import entry
from ops import receiving, refunds, returns
from promo import credits

FAILURES = []


def check(name, got, want):
    if got != want:
        FAILURES.append(f"{name}: got {got!r}, want {want!r}")


def main():
    check("full return refunds the whole total",
          refunds.refund_amount("40.00", 4, 4), Decimal("40.00"))
    for bad in ((0, 4), (5, 4), (1, 0)):
        try:
            refunds.refund_amount("40.00", bad[0], bad[1])
        except ValueError:
            pass
        else:
            FAILURES.append(f"refund_amount accepted {bad}")

    with tempfile.TemporaryDirectory() as tmp:
        returns.accept_return(tmp, "RMA-1", "SKU-9", 2)
        receiving.receive_shipment(tmp, "PO-1", "SKU-9", 7)
        rows = entry.read(tmp)
        check("both bookings reached the ledger", len(rows), 2)
        check("return booked its units", rows[0].get("units"), 2)
        check("receiving booked its units", rows[1].get("units"), 7)

    with tempfile.TemporaryDirectory() as tmp:
        issued = credits.issue_credit(tmp, "CUST-1", "12.5", "goodwill")
        check("credit normalises to cents", issued["dollars"], "12.50")

    if FAILURES:
        for failure in FAILURES:
            print(f"FAIL {failure}")
        return 1
    print("ok")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
